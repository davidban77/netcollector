"""Module which holds output format definitions of modeled data."""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module

from line_protocol_parser import parse_line


class InfluxMetric(BaseModel):  # pylint: disable=too-few-public-methods
    """Influx Line Protocol Model."""

    name: str
    tags: Dict[str, Any] = Field(default_factory=dict)
    influx_fields: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[int]

    def to_line_protocol(self):
        """Transform model to influx line protocol string.
        Returns:
            str: Influx line protcol metric
        """
        return format_influx_metrics(series=self.name, data=self.influx_fields, tags=self.tags)


def format_influx_metrics(
    series: str, data: Dict[str, Any], tags: Dict[str, Any] = {}
):  # pylint: disable=dangerous-default-value
    """Format data into influx compatible string.
    Args:
        series (str): Name of measurement
        data (dict): Dictionary of the results to print out for influx
        tags (dict, optional): Key and avalues to be set as tag in the metric
    """
    tags_string = ""
    for key, value in tags.items():
        if value is not None:
            if isinstance(value, str):
                value = value.replace(" ", r"\ ")
            tags_string += f",{key}={value}"

    data_string = ""
    for key, value in data.items():
        if data_string:
            data_string += ","
        if isinstance(value, int):
            data_string += f"{key}={value}i"
        elif isinstance(value, str):
            value = value.replace(" ", r"\ ")
            data_string += f'{key}="{value}"'
        elif isinstance(value, bool):
            data_string += f"{key}=true" if value else f"{key}=false"
        else:
            data_string += f"{key}={value}"

    return f"{series}{tags_string} {data_string}"


def parse_influx_metrics(series: str) -> InfluxMetric:
    """Create Influx Metric model from ingested string.
    Args:
        series (str): Influx line protocol string.
    Returns:
        InfluxMetric: Influx Metric model.
    """
    data = parse_line(series)
    return InfluxMetric(
        name=data["measurement"], tags=data["tags"], influx_fields=data["fields"], timestamp=data["time"]
    )
