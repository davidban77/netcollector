"""Module which holds BGP Session data model and the respective processors that generate it."""
from typing import List, Optional
from pydantic import IPvAnyAddress
from netcollector.commander import Command
from netcollector.connector import ConnectParams
from .influx import format_influx_metrics
from .base import BaseResourceModel


SESSION_STATE_MAP = {
    "idle": 1,
    "connect": 2,
    "active": 3,
    "opensent": 4,
    "openconfirm": 5,
    "established": 6,
}


class BgpSessionError(Exception):
    pass


def bgp_type(raw_type: str) -> str:
    """Transforms passed BGP neighbor type to a standard value.
    Args:
        raw_type (str): Passed raw data
    Returns:
        str: EXTERNAL or INTERNAL, else remains the same
    Examples:
        >>> bgp_type("external peer")
        'EXTERNAL'
        >>> bgp_type("iBGP")
        'INTERNAL'
    """
    if any(x in raw_type.lower() for x in ("external", "ebgp")):
        peer_type = "EXTERNAL"
    elif any(x in raw_type.lower() for x in ("internal", "ibgp")):
        peer_type = "INTERNAL"
    else:
        peer_type = raw_type

    return peer_type


def strip_ip_address(raw_address: str) -> str:
    """Parses IP string information that may contain port information and strips it.
    Args:
        raw_address (str): Raw IP string information typically returned from junos parsed data
    Returns:
        str: IP string information
    Examples:
        >>> strip_ip_address("192.168.7.7+179")
        '192.168.7.7'
        >>> strip_ip_address("192.168.4.4")
        '192.168.4.4'
    """
    return raw_address.split("+")[0] if "+" in raw_address else raw_address


class BgpSession(BaseResourceModel):
    """BGP Base Session.
    """

    local_address: Optional[IPvAnyAddress] = None
    neighbor_address: Optional[IPvAnyAddress] = None
    local_as: Optional[int] = None
    peer_as: Optional[int] = None
    peer_router_id: Optional[IPvAnyAddress] = None
    router_id: Optional[IPvAnyAddress] = None
    peer_type: Optional[str] = None
    routing_instance: str = "default"
    # export_policy: Optional[str] = None
    # import_policy: Optional[str] = None
    # flaps: Optional[int] = None
    # active_holdtime: Optional[int] = None
    # keepalive_interval: Optional[int] = None
    # group_index: Optional[int] = None
    # peer_index: Optional[int] = None
    peer_group: Optional[str] = None
    prefixes_denied: Optional[int] = None
    prefixes_suppressed: Optional[int] = None
    prefixes_received: Optional[int] = None
    prefixes_received_pre_policy: Optional[int] = None
    prefixes_sent: Optional[int] = None
    prefixes_installed: Optional[int] = None
    session_state: Optional[str] = None
    session_state_code: Optional[int] = None

    def influx_metric(self) -> str:
        """Outputs InfluxDB Line protocol.
        Returns:
            str: Influx line protocol style
        """
        tags = {}
        fields = {}
        for key, value in self.dict().items():
            if key in [
                "local_address",
                "neighbor_address",
                "local_as",
                "peer_as",
                "peer_router_id",
                "router_id",
                "peer_type",
                "routing_instance",
                "peer_group",
            ]:
                if value is None:
                    continue
                tags.update({key: value})
            elif key in [
                "prefixes_received",
                "prefixes_received_pre_policy",
                "prefixes_sent",
                "prefixes_installed",
                "session_state_code",
            ]:
                if value is None:
                    continue
                if key == "session_state_code":
                    fields.update({"session_state": value})
                else:
                    fields.update({key: value})
        return format_influx_metrics("bgp", data=fields, tags=tags)


def netmiko_processor(commands: List[Command], connector: ConnectParams) -> List[BgpSession]:
    """Processes Netmiko parsed data and returns BGP Session modeled data.
    Args:
        commands (List[Command]): List of commands and their results
        connector (ConnectParams): Connection and device parameters
    Raises:
        CollectorError: When no command was passed or if no result was passed either
        NotImplementedError: Netmiko parser not implemented yet or not supported
    Returns:
        List[BgpSession]: List of BGP Session modeled data
    """
    command = commands[0]
    if not command:
        raise BgpSessionError("No command found")
    if not command.result:
        raise BgpSessionError("No result returned in Command")

    bgp_sessions = []
    if connector.device_type == "cisco_ios" or connector.device_type == "cisco_xe":

        if command.params.get("use_textfsm"):
            for item in command.result:
                bgp_sessions.append(
                    BgpSession(
                        local_address=item["localhost_ip"],
                        neighbor_address=item["remote_ip"],
                        peer_as=item["remote_as"],
                        peer_router_id=item["remote_router_id"],
                        session_state=item["bgp_state"].lower(),
                        session_state_code=SESSION_STATE_MAP.get(item["bgp_state"].lower()),
                        peer_group=item["peer_group"] if item["peer_group"] else None,
                    )
                )
        elif command.params.get("use_genie"):
            for vrf_name, vrf in command.result.get("vrf", {}).items():
                for neighbor_ip, data in vrf.get("neighbor", {}).items():
                    bgp_sessions.append(
                        BgpSession(
                            local_address=data.get("bgp_session_transport", {}).get("transport", {}).get("local_host"),
                            neighbor_address=neighbor_ip,
                            peer_as=data.get("remote_as"),
                            router_id=data.get("router_id"),
                            session_state=data["session_state"].lower(),
                            session_state_code=SESSION_STATE_MAP.get(data["session_state"].lower()),
                            routing_instance=vrf_name,
                            prefixes_received=data.get("address_family", {})
                            .get("ipv4 unicast", {})
                            .get("prefix_activity_counters", {})
                            .get("received", {})
                            .get("prefixes_current"),
                            prefixes_sent=data.get("address_family", {})
                            .get("ipv4 unicast", {})
                            .get("prefix_activity_counters", {})
                            .get("sent", {})
                            .get("prefixes_current"),
                            prefixes_installed=data.get("address_family", {})
                            .get("ipv4 unicast", {})
                            .get("prefix_activity_counters", {})
                            .get("received", {})
                            .get("used_as_bestpath"),
                        )
                    )

        else:
            raise NotImplementedError("Netmiko parser not implemented")

    else:
        raise NotImplementedError("Not yet for other device types")

    return bgp_sessions


def pyez_processor(
    commands: List[Command], connector: ConnectParams  # pylint: disable=unused-argument
) -> List[BgpSession]:
    """Processes PyEZ parsed data and returns BGP Session modeled data.
    Args:
        commands (List[Command]): List of commands and their results
        connector (ConnectParams): Connection and device parameters
    Raises:
        CollectorError: When no command was passed or if no result was passed either
        NotImplementedError: Netmiko parser not implemented yet or not supported
    Returns:
        List[BgpSession]: List of BGP Session modeled data
    """
    command = commands[0]
    if not command:
        raise BgpSessionError("No command found")
    if not command.result:
        raise BgpSessionError("No result returned in Command")

    bgp_sessions = list()
    for item in command.result:

        if command.params.get("table"):

            # Calculate denied prefixes
            prefixes_received = int(item.prefixes_accepted) if item.prefixes_accepted else 0
            prefixes_received_pre_policy = int(item.prefixes_received) if item.prefixes_received else 0
            prefixes_denied = prefixes_received_pre_policy - prefixes_received

            bgp_sessions.append(
                BgpSession(
                    local_address=strip_ip_address(item.local_address),  # type: ignore
                    neighbor_address=strip_ip_address(item.peer_address),  # type: ignore
                    local_as=item.local_as,
                    peer_as=item.peer_as,
                    peer_router_id=strip_ip_address(item.peer_id) if item.peer_id else None,  # type: ignore
                    router_id=strip_ip_address(item.local_id) if item.local_id else None,  # type: ignore
                    # description=item.desc,
                    peer_type=bgp_type(item.peer_type),
                    # export_policy=item.export_policy,
                    # import_policy=item.import_policy,
                    # flaps=item.flap_count,
                    # active_holdtime=item.active_holdtime if item.active_holdtime else None,
                    # keepalive_interval=item.keepalive_interval if item.keepalive_interval else None,
                    # group_index=item.group_index if item.group_index else None,
                    # peer_index=item.peer_index if item.peer_index else None,
                    prefixes_received_pre_policy=prefixes_received_pre_policy,
                    prefixes_received=prefixes_received,
                    prefixes_denied=prefixes_denied,
                    prefixes_installed=item.prefixes_active if item.prefixes_active else 0,
                    prefixes_suppressed=item.prefixes_suppressed if item.prefixes_suppressed else 0,
                    prefixes_sent=item.prefixes_advertised if item.prefixes_advertised else 0,
                    session_state=item.peer_state.lower(),
                    session_state_code=SESSION_STATE_MAP.get(item.peer_state.lower()),
                )
            )
        else:
            raise NotImplementedError("PyEZ parser not implemented")

    return bgp_sessions