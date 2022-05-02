"""Module which holds commands definitions and exector map."""
import uuid
from typing import Dict, List, Literal, Tuple, Any, Optional
from datetime import datetime
from pydantic import BaseModel


class CommanderError(Exception):
    pass


EXECUTOR_MAP: Dict[Tuple[str, str], Dict[str, Any]] = {
    ("cisco_xe", "interface"): {
        "ssh": {
            "executor": "netmiko",
            "commands": ["show interfaces"],
            "params": {"use_genie": True},
        }
    },
    ("cisco_asa", "vpn_session"): {
        "ssh": {
            "executor": "netmiko",
            "commands": ["show vpn-sessiondb"],
            "params": {"use_textfsm": True},
        }
    },
    ("cisco_ios", "bgp_session"): {
        "ssh": {
            "executor": "netmiko",
            "commands": ["show bgp all neighbor"],
            "params": {"use_genie": True},
        }
    },
    ("cisco_ios", "lldp_neighbors"): {
        "ssh": {
            "executor": "netmiko",
            "commands": ["show lldp neighbors"],
            "params": {"use_textfsm": True},
        }
    },
    ("cisco_xe", "bgp_session"): {
        "ssh": {
            "executor": "netmiko",
            "commands": ["show ip bgp neighbors"],
            "params": {"use_genie": True},
        }
    },
    ("juniper_junos", "bgp_session"): {
        "netconf": {
            "executor": "pyez",
            "commands": ["get-bgp-neighbor-information"],
            "params": {"table": "NtcBgpTable"},
        }
    },
}


class Command(BaseModel):
    """Base Command model. It holds command related data to be executed on a device.
    Args:
        BaseModel: Pydantic base model
    """

    executor: str
    collector: str
    collection_method: Literal["ssh", "netconf", "snmp"]
    command: str
    params: Dict[str, Any] = dict()
    result: Optional[Any] = None
    id: str = str(uuid.uuid4())
    timestamp: Optional[datetime] = None
    start_time: Optional[datetime] = None
    execution_time: Optional[float] = None

    def start_timing(self):
        self.start_time = datetime.now()

    def stop_timing(self):
        self.timestamp = datetime.now()
        if self.start_time:
            self.execution_time = (self.timestamp - self.start_time).total_seconds()


def create_commands(  # pylint: disable=dangerous-default-value
    device_type: str,
    collectors: List[Tuple[str, Literal["ssh", "netconf", "snmp"]]],
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
    for collector, collection_method in collectors:
        try:
            directives = executor_map[(device_type, collector)][collection_method]
        except KeyError:
            raise CommanderError(
                f"Unable to determine executor for: device_type='{device_type}', collector='{collector}', "
                f"collection_method={collection_method}"
            )

        commands.extend(
            Command(
                command=_command,
                executor=directives["executor"],
                collector=collector,
                collection_method=collection_method,
                params=directives.get("params", {}),
            )
            for _command in directives["commands"]
        )

    return commands
