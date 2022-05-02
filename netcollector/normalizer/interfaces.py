"""Interfaces data normalization."""
from typing import List, Literal, Optional
from pydantic import IPvAnyInterface, Field
from netaddr import EUI
from netcollector.commander import Command
from netcollector.connector import ConnectParams
from .base import BaseResourceModel


class InterfacesError(Exception):
    pass


def mac_converter(address: str) -> str:
    if address.startswith("0x"):
        address = int(address, 16)  # type: ignore

    mac = EUI(address)

    return str(mac).replace("-", ":").lower()


class PortChannel(BaseResourceModel):
    port_channel_member: bool

    class Config:
        validate_assignment = True
        extra = "allow"


class InterfaceIP(BaseResourceModel):
    address: Optional[IPvAnyInterface] = None
    role: Optional[Literal["primary", "secondary"]] = None


class InterfaceCounters(BaseResourceModel):
    in_pkts: Optional[int] = None
    in_octets: Optional[int] = None
    in_multicast_pkts: Optional[int] = None
    in_broadcast_pkts: Optional[int] = None
    in_runts: Optional[int] = None
    in_giants: Optional[int] = None
    in_throttles: Optional[int] = None
    in_errors: Optional[int] = None
    in_crc_errors: Optional[int] = None
    out_pkts: Optional[int] = None
    out_octets: Optional[int] = None
    out_multicast_pkts: Optional[int] = None
    out_broadcast_pkts: Optional[int] = None
    out_errors: Optional[int] = None
    out_collision: Optional[int] = None
    out_unknown_protocl_drops: Optional[int] = None
    out_late_collision: Optional[int] = None
    out_deferred: Optional[int] = None
    out_lost_carrier: Optional[int] = None
    out_no_carrier: Optional[int] = None


class Interface(BaseResourceModel):
    name: str
    enabled: bool
    oper_status: Literal["up", "down"]
    description: Optional[str] = None
    line_protocol: Optional[Literal["up", "down"]] = None
    port_channel: Optional[PortChannel] = None
    type: Optional[str] = None
    mac_address: Optional[str] = None
    # phys_address: str
    ipv4: List[InterfaceIP] = Field(default_factory=list)
    ipv6: List[InterfaceIP] = Field(default_factory=list)
    delay: Optional[int] = None
    mtu: Optional[int] = None
    bandwidth: Optional[int] = None
    duplex_mode: Optional[str] = None
    port_speed: Optional[str] = None
    counters: Optional[InterfaceCounters] = None


def netmiko_processor(command: Command, connector: ConnectParams) -> List[Interface]:
    """Processes Netmiko parsed data."""
    if not command.result:
        raise InterfacesError("No result returned in Command")

    intfs = []
    if command.params.get("use_genie"):
        for intf_name, intf_params in command.result.items():
            _pc = None if not intf_params.get("port_channel") else PortChannel(**intf_params.get("port_channel", {}))
            _ic = None
            if intf_params.get("counters"):
                _ic = InterfaceCounters(
                    in_pkts=intf_params["counters"].get("in_pkts"),
                    in_octets=intf_params["counters"].get("in_octets"),
                    in_multicast_pkts=intf_params["counters"].get("in_multicast_pkts"),
                    in_broadcast_pkts=intf_params["counters"].get("in_broadcast_pkts"),
                    in_runts=intf_params["counters"].get("in_runts"),
                    in_giants=intf_params["counters"].get("in_giants"),
                    in_throttles=intf_params["counters"].get("in_throttles"),
                    in_errors=intf_params["counters"].get("in_errors"),
                    in_crc_errors=intf_params["counters"].get("in_crc_errors"),
                    out_pkts=intf_params["counters"].get("out_pkts"),
                    out_octets=intf_params["counters"].get("out_octets"),
                    out_multicast_pkts=intf_params["counters"].get("out_multicast_pkts"),
                    out_broadcast_pkts=intf_params["counters"].get("out_broadcast_pkts"),
                    out_errors=intf_params["counters"].get("out_errors"),
                    out_collision=intf_params["counters"].get("out_collision"),
                    out_unknown_protocl_drops=intf_params["counters"].get("out_unknown_protocl_drops"),
                    out_late_collision=intf_params["counters"].get("out_late_collision"),
                    out_deferred=intf_params["counters"].get("out_deferred"),
                    out_lost_carrier=intf_params["counters"].get("out_lost_carrier"),
                    out_no_carrier=intf_params["counters"].get("out_no_carrier"),
                )
            intfs.append(Interface(
                name=intf_name,
                enabled=intf_params["enabled"],
                oper_status=intf_params["oper_status"].lower(),
                description=intf_params.get("description"),
                line_protocol=intf_params.get("line_protocol"),
                port_channel=_pc,
                type=intf_params.get("type"),
                mac_address=mac_converter(intf_params.get("mac_address")),
                ipv4=[InterfaceIP(address=ip) for ip, _ in intf_params.get("ipv4", {}).items()],
                ipv6=[InterfaceIP(address=ip) for ip, _ in intf_params.get("ipv6", {}).items()],
                delay=intf_params.get("delay"),
                mtu=intf_params.get("mtu"),
                bandwidth=intf_params.get("bandwidth"),
                duplex_mode=intf_params.get("duplex_mode"),
                port_speed=intf_params.get("port_speed"),
                counters=_ic
            ))

    else:
        raise NotImplementedError("Not yet implemented for other methods")

    return intfs
