"""Main session and commmand dispatcher module to execute on target devices."""
import importlib
from typing import List, Optional, Tuple
from jnpr.junos import Device
from netmiko import ConnectHandler, BaseConnection
from .commander import Command
from .connector import ConnectParams

JUNOS_CUSTOM_MODULES = "netcollector.extras.junos_tables"
JUNOS_PYEZ_MODULES = "jnpr.junos.op"


class DispatcherError(Exception):
    pass


class NetmikoError(DispatcherError):
    pass


class PyezError(DispatcherError):
    pass


class NetmikoDispatcher:  # pylint: disable=too-few-public-methods
    """Netmiko Dispatcher to interact with a target device.
    Raises:
        NetmikoError: Netmiko related issues
    """

    outter_dev: Optional[BaseConnection] = None

    class NetmikoDispatcherDev:
        def __init__(self, connector):
            self.connector = connector

        def __enter__(self):
            if not NetmikoDispatcher.outter_dev:
                NetmikoDispatcher.outter_dev = ConnectHandler(
                    host=self.connector.host,
                    username=self.connector.username,
                    password=self.connector.password.get_secret_value(),
                    secret=self.connector.secret.get_secret_value() if self.connector.secret else None,
                    device_type=self.connector.device_type,
                    session_timeout=self.connector.timeout,
                    keepalive=self.connector.keepalive,
                    port=self.connector.ssh_port,
                )

            return NetmikoDispatcher.outter_dev

        def __exit__(self, type, value, traceback):
            if not self.connector.persist:
                if NetmikoDispatcher.outter_dev:
                    NetmikoDispatcher.outter_dev.disconnect()

                NetmikoDispatcher.outter_dev = None

    @classmethod
    def execute(cls, commands: List[Command], connector: ConnectParams) -> Tuple[Optional[DispatcherError], str]:
        """Execute a list of commands using netmiko driver.
        Args:
            commands (List[Command]): List of Command to execute
            connector (ConnectParams): Connection and device parameters
        Raises:
            NetmikoError: Netmiko related issues
        """
        error = None
        msg = ""
        try:
            with cls.NetmikoDispatcherDev(connector=connector) as dev:
                for command in commands:
                    # command.params usually has parsing technique like use_genie=True
                    command.start_timing()
                    command.result = dev.send_command(command.command, **command.params)
                    command.stop_timing()
        except Exception as err:
            # raise NetmikoError(f"Driver failed execution: {err}") from err
            msg = f"Driver failed execution: {err}"
            error = NetmikoError(msg)
        return error, msg


class PyEZDispatcher:  # pylint: disable=too-few-public-methods
    """PyEZ Dispatcher to interact with a target device.
    Raises:
        PyezError: PyEZ related issues
    """

    @staticmethod
    def execute(commands: List[Command], connector: ConnectParams) -> Tuple[Optional[DispatcherError], str]:
        """Execute a list of commands using junos-eznc driver.
        It supports 2 methods to collect and parse the data.
        - Using the `table and view` method. See: https://www.juniper.net/documentation/en_US/junos-pyez/topics/concept/junos-pyez-tables-and-views-overview.html
        - Using the `rpc` method.
        Args:
            commands (List[Command]): List of Command to execute
            connector (ConnectParams): Connection and device parameters
        Raises:
            PyezError: PyEZ related issues
        """
        error = None
        msg = ""
        conn_data = dict(
            host=connector.host,
            user=connector.username,
            passwd=connector.password.get_secret_value(),
            port=connector.netconf_port,
        )
        try:
            with Device(**conn_data) as dev:
                for command in commands:
                    if command.params.get("table"):
                        # Junos tables are made on a per protocol: i.e "bgp", and holds tables for the different metrics
                        # For example te NtcBgpTable returns data for bgp_session collector. So we need to know the
                        # protocol to then load the table.
                        protocol = command.collector.split("_")[0] if "_" in command.collector else command.collector

                        try:
                            # Dynamically and explicitly import the module and table for data collection/parsing
                            module = importlib.import_module(f"{JUNOS_CUSTOM_MODULES}.{protocol}")

                            # The table is loaded dynamically from the <protocol>.<table>.
                            # For example this line could be read as: table = bgp.NtcBgpTable(dev)
                            command.start_timing()
                            table = getattr(module, command.params["table"])(dev)
                            command.stop_timing()
                        except (ModuleNotFoundError, AttributeError):

                            # If module or table is not available in JUNOS_CUSTOM_MODULES, try with the Pyez ones
                            try:
                                module = importlib.import_module(f"{JUNOS_PYEZ_MODULES}.{protocol}")
                                command.start_timing()
                                table = getattr(module, command.params["table"])(dev)
                                command.stop_timing()
                            except ModuleNotFoundError as err:
                                msg = (
                                    f"Driver execution failed: Module {protocol} not found in custom nor PyEZ tables." f"\nNative error: {err}"
                                )
                                error = PyezError(msg)
                                return error, msg

                            except AttributeError as err:
                                msg = (
                                    f"Driver execution failed: Table {command.params['table']} for module "
                                    f"{protocol} not found in custom nor PyEZ tables.\nNative error: {err}"
                                )
                                error = PyezError(msg)
                                return error, msg

                        command.result = table.get()
                    else:
                        command.result = dev.rpc.get(command.command)
        except Exception as err:
            msg = f"Driver failed execution (unknown exception): {err}"
            error = PyezError(msg)
        return error, msg
