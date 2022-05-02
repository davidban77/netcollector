"""Module which holds LLDP Neighbors data model and the repective processors that generates it."""
from typing import Optional, List

from .influx import format_influx_metrics

from pydantic import BaseModel
from netcollector.commander import Command
from netcollector.connector import ConnectParams


class LLDPNeighborError(Exception):
    pass


class LLDPNeighbor(BaseModel):
    """LLDP Neighbors data model.
    Args:
        BaseModel: Base Collector data model
    """

    interface: str
    local_parent_interface: Optional[str] = None
    remote_type: Optional[str] = None
    remote_chassis_id: Optional[str] = None
    remote_port_desc: Optional[str] = None
    remote_interface: Optional[str] = None
    remote_system_name: Optional[str] = None

    def influx_metric(self) -> str:
        """Outputs InfluxDB Line protocol.
        Returns:
            str: Influx line protocol style
        """
        tags = {}
        fields = {}
        for key, value in self.dict().items():
            if key in [
                "interface",
                "local_parent_interface",
                "remote_type",
                "remote_chassis_id",
                "remote_port_desc",
                "remote_interface",
                "remote_system_name",
            ]:
                if value is None:
                    continue
                tags.update({key: value})
            elif key in [
                # "prefixes_received",
                # "prefixes_received_pre_policy",
                # "prefixes_sent",
                # "prefixes_installed",
                # "prefixes_installed",
                # "session_state_code",
                "remote_interface",
            ]:
                if value is None:
                    continue
                fields.update({key: value})
        return format_influx_metrics("lldp_neighbors", data=fields, tags=tags)


def netmiko_processor(commands: List[Command], connector: ConnectParams) -> List[LLDPNeighbor]:
    """Processes Netmiko parsed data and returns LLDP Neighbor modeled data.
    Args:
        commands (List[Command]): List of commands and their results
        connector (ConnectParams): Connection and device parameters
    Raises:
        CollectorError: When no command was passed or if no result was passed either
        NotImplementedError: Netmiko parser not implemented yet or not supported
    Returns:
        List[LldpNeighbor]: List of LLDP Neighbor modeled data
    """
    command = commands[0]
    if not command:
        raise LLDPNeighborError("No command found")
    if not command.result:
        raise LLDPNeighborError("No result returned in Command")

    lldp_neighbors = []
    if connector.device_type == "cisco_ios" or connector.device_type == "cisco_xe":

        if command.params.get("use_textfsm"):
            for item in command.result:
                lldp_neighbors.append(
                    LLDPNeighbor(
                        interface=item["local_interface"],
                        remote_system_name=item["neighbor"],
                        remote_interface=item["neighbor_interface"],
                    )
                )

        else:
            raise NotImplementedError("Netmiko parser not implemented")

    else:
        raise NotImplementedError("Not yet for other device types")

    return lldp_neighbors