from typing import List, Union
from netcollector.commander import Command
from netcollector.connector import ConnectParams
from . import bgp_sessions, lldp_neighbors, vpn_sessions, interfaces
from .base import BaseResourceModel

NORMALIZER_MODULES = {
    "interface": interfaces,
    "bgp_session": bgp_sessions,
    "lldp_neighbors": lldp_neighbors,
    "vpn_session": vpn_sessions,
}


def normalize_data(command: Command, connector: ConnectParams) -> Union[BaseResourceModel, List[BaseResourceModel]]:
    normalizer_module = NORMALIZER_MODULES[command.collector]
    return getattr(normalizer_module, f"{command.executor}_processor")(command, connector)
