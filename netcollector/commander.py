"""Module which holds commands definitions and exector map."""
from typing import Dict, List, Tuple, Any, Optional
from pydantic import BaseModel


class CommanderError(Exception):
    pass


EXECUTOR_MAP: Dict[Tuple[str, str], Dict[str, Any]] = {
    ("cisco_asa", "vpn_session"): dict(
        executor="netmiko", commands=["show vpn-sessiondb"], params=dict(use_textfsm=True)
    ),
    ("cisco_ios", "bgp_session"): dict(
        executor="netmiko", commands=["show bgp all neighbor"], params=dict(use_genie=True)
    ),
    ("cisco_ios", "lldp_neighbors"): dict(
        executor="netmiko", commands=["show lldp neighbors"], params=dict(use_textfsm=True)
    ),
    ("cisco_xe", "bgp_session"): dict(
        executor="netmiko", commands=["show ip bgp neighbors"], params=dict(use_genie=True)
    ),
    ("juniper_junos", "bgp_session"): dict(
        executor="pyez", commands=["get-bgp-neighbor-information"], params=dict(table="NtcBgpTable")
    ),
}


class Command(BaseModel):
    """Base Command model. It holds command related data to be executed on a device.
    Args:
        BaseModel: Pydantic base model
    """

    executor: str
    collector: str
    command: str
    params: Dict[str, Any] = dict()
    result: Optional[Any] = None


def create_commands(  # pylint: disable=dangerous-default-value
    device_type: str,
    collectors: List[str],
    executor_map: Dict[Tuple[str, str], Dict[str, Any]] = EXECUTOR_MAP,
) -> List[Command]:
    """Creates a list of Command instances.
    These are created based on the combination of device_type and a collector. It then returns a command instance
    with parameters, commands and the executor (i.e. netmiko) for later execution.
    To see available options see `EXECUTOR_MAP`
    Args:
        device_type (str): Device type
        collectors (List[str]): Collectors to be used
        executor_map (Dict[Tuple[str, str], Dict[str, Any]]): Mapping data structure that correlates device_type and
        collect with a directive that holds the executor (driver), commands and extra parameters for parsing the data.
        Defaults to `EXECUTOR_MAP`
    Raises:
        CollectorError: When it is unable to determine which executor to use.
    Returns:
        List[Command]: List of Command instances
    """
    commands: List[Command] = []
    for collector in collectors:
        try:
            directives = executor_map[(device_type, collector)]
        except KeyError:
            raise CommanderError(
                f"Unable to determine executor for: device_type='{device_type}', collector='{collector}'"
            )

        commands.extend(
            Command(
                command=_command,
                executor=directives["executor"],
                collector=collector,
                params=directives.get("params", {}),
            )
            for _command in directives["commands"]
        )

    return commands
