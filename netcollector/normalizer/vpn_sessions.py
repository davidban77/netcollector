"""Module which holds VPN Session data model and the respective processors that generate it."""
import re
from typing import Optional
from .influx import format_influx_metrics
from .base import BaseResourceModel


class VpnSessionsError(Exception):
    pass


def isinty(value):
    """Converts to integer if possible."""
    try:
        return int(value)
    except ValueError:
        return None


def slugify(string: str, length: int = 50) -> str:
    string = re.sub(r"[^\-\.\w\s]", "", string)
    string = string.strip().lower()
    string = re.sub(r"[\-\.\s]+", "-", string)
    string = string.encode("ASCII", "ignore").decode()

    return string[:length]


class AsaVpnStats(BaseResourceModel):
    active: Optional[int] = None
    cumulative: Optional[int] = None
    peak_concurrent: Optional[int] = None
    inactive: Optional[int] = None
    name: Optional[str] = None

    def influx_metric(self) -> str:
        tags = {}
        fields = {}
        for key, value in self.dict().items():
            if key in [
                "name",
            ]:
                if value is None:
                    continue
                tags.update({key: value})
            elif key in [
                "active",
                "cumulative",
                "peak_concurrent",
                "inactive",
            ]:
                if value is None:
                    continue
                fields.update({key: value})

        return format_influx_metrics("vpn_session", data=fields, tags=tags)


class AsaTunnelStats(BaseResourceModel):
    active: Optional[int] = None
    cumulative: Optional[int] = None
    peak_concurrent: Optional[int] = None
    name: Optional[str] = None

    def influx_metric(self) -> str:
        tags = {}
        fields = {}
        for key, value in self.dict().items():
            if key in [
                "name",
            ]:
                if value is None:
                    continue
                tags.update({key: value})
            elif key in [
                "active",
                "cumulative",
                "peak_concurrent",
            ]:
                if value is None:
                    continue
                fields.update({key: value})

        return format_influx_metrics("vpn_tunnel", data=fields, tags=tags)


class AsaGlobalStats(BaseResourceModel):
    total_active_and_inactive: Optional[int] = None
    total_cumulative: Optional[int] = None
    device_total_vpn_capacity: Optional[int] = None
    device_load_percent: Optional[int] = None
    totals_active: Optional[int] = None
    totals_cumulative: Optional[int] = None

    def influx_metric(self) -> str:
        tags = {}
        fields = {}
        for key, value in self.dict().items():
            if key in []:
                if value is None:
                    continue
                tags.update({key: value})
            elif key in [
                "total_active_and_inactive",
                "total_cumulative",
                "device_total_vpn_capacity",
                "device_load_percent",
                "totals_active",
                "totals_cumulative",
            ]:
                if value is None:
                    continue
                fields.update({key: value})

        return format_influx_metrics("asa_vpn", data=fields, tags=tags)


def netmiko_processor(commands, connector):
    """Processes Netmiko parsed data and returns VPN Session modeled data."""
    command = commands[0]
    if not command:
        raise VpnSessionsError("No command found")
    if not command.result:
        raise VpnSessionsError("No result returned in Command")

    stats = []
    if connector.device_type == "cisco_asa":
        sessiondb = command.result

        try:
            for i, _ in enumerate(sessiondb[0]["vpn_session_name"]):
                stat = AsaVpnStats(
                    active=isinty(sessiondb[0]["vpn_session_active"][i]),
                    cumulative=isinty(sessiondb[0]["vpn_session_cumulative"][i]),
                    peak_concurrent=isinty(sessiondb[0]["vpn_session_peak_concurrent"][i]),
                    inactive=isinty(sessiondb[0]["vpn_session_inactive"][i]),
                    name=slugify(sessiondb[0]["vpn_session_name"][i]),
                )
                stats.append(stat)
        except (IndexError, KeyError):
            raise VpnSessionsError("Unable to parse output correctly (vpn_session)")

        try:
            for i, _ in enumerate(sessiondb[0]["tunnels_summary_name"]):
                stat = AsaTunnelStats(
                    active=isinty(sessiondb[0]["tunnels_summary_active"][i]),
                    cumulative=isinty(sessiondb[0]["tunnels_summary_cumulative"][i]),
                    peak_concurrent=isinty(sessiondb[0]["tunnels_summary_peak_concurrent"][i]),
                    name=slugify(sessiondb[0]["tunnels_summary_name"][i]),
                )
                stats.append(stat)
        except (IndexError, KeyError):
            raise VpnSessionsError("Unable to parse output correctly (tunnels)")

        stat = AsaGlobalStats(
            total_active_and_inactive=isinty(sessiondb[0]["total_active_and_inactive"]),
            total_cumulative=isinty(sessiondb[0]["total_cumulative"]),
            device_total_vpn_capacity=isinty(sessiondb[0]["device_total_vpn_capacity"]),
            device_load_percent=isinty(sessiondb[0]["device_load_percent"]),
            totals_active=isinty(sessiondb[0]["totals_active"]),
            totals_cumulative=isinty(sessiondb[0]["totals_cumulative"]),
        )
        stats.append(stat)

    else:
        raise NotImplementedError("Not yet for other device types")

    return stats
