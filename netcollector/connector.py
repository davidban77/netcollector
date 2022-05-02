"""Module which holds connector definition."""
import os
from typing import Optional
from pydantic import BaseModel, SecretStr


class ConnectParams(BaseModel):
    """Connection Parameters Object to be used for dispatcher service.
    Args:
        BaseModel: Pydantic Base Model
    """

    host: str
    device_type: str
    persist: bool
    username: str
    password: SecretStr
    secret: Optional[SecretStr] = None
    timeout: int = 60
    keepalive: int = 10
    ssh_port: int = 22
    netconf_port: int = 830

    class Config:  # pylint: disable=too-few-public-methods
        """Base Configuration class for Pydantic Model."""

        validate_assignment = True


def create_connector(
    host: str,
    device_type: str,
    persist: bool,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> ConnectParams:
    """Creates a ConnectParams object used to connect to devices.
    Args:
        host (str): Target hostname or IP Address
        device_type (str): Supported device type
        username (str): (Optional) Username to connect to device. Defaults to `COLLECTOR_USER` environment variable
        device_type (str): (Optional) Password to connect to device. Defaults to `COLLECTOR_PASSWORD` environment
        variable
    Exits:
        CollectorError: If unable to find Username or Password in environment variables
    Returns:
        ConnectParams: Connection parameters object
    """
    _pass = password if password is not None else os.getenv("COLLECTOR_PASSWORD", "")
    return ConnectParams(
        host=host,
        device_type=device_type,
        username=username if username is not None else os.getenv("COLLECTOR_USER", ""),
        password=_pass,  # type: ignore
        secret=os.getenv("COLLECTOR_SECRET", _pass),  # type: ignore
        timeout=int(os.getenv("COLLECTOR_TIMEOUT", "60")),
        keepalive=int(os.getenv("COLLECTOR_KEEPALIVE", "10")),
        ssh_port=int(os.getenv("COLLECTOR_SSH_PORT", "22")),
        netconf_port=int(os.getenv("COLLECTOR_NETCONF_PORT", "830")),
        persist=persist,
    )
