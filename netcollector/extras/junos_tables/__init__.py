"""Junos External Tables and View used by PyEZ library.
For more information see: https://www.juniper.net/documentation/en_US/junos-pyez/topics/task/program/junos-pyez-tables-views-loading.html#task-tables-views-importing-external
Initilisation code similar to PyEZ jnpr.junos.op module, which dynamically creates modules based on YAML files
specifications.
"""
import sys
import os
import types
from typing import List

import yaml
from jnpr.junos.factory.factory_loader import FactoryLoader

__all__: List[str] = []


class MetaPathFinder:  # pylint: disable=too-few-public-methods
    """Finder class used to dynamically find modules"""

    def find_module(self, fullname: str, *args):  # pylint: disable=inconsistent-return-statements
        # pylint: disable=unused-argument,no-self-use
        """Finds modules from a given path
        Args:
            fullname (str): Fullname (path)
        Returns:
            Loader instance
        """
        if fullname.startswith("network_collector.cli.collectors.junos_tables"):
            mod = fullname.split(".")[-1]
            if mod in [os.path.splitext(i)[0] for i in os.listdir(os.path.dirname(__file__))]:
                return MetaPathLoader()


class MetaPathLoader:  # pylint: disable=too-few-public-methods
    """Loader class used to dynamically load modules from YAML files specifications"""

    def load_module(self, fullname: str):
        # pylint: disable=no-self-use
        """Loads module from YAML file specification
        Args:
            fullname (str): Fullname (path)
        Raises:
            ImportError: When module is not loaded
        Returns:
            A module type object
        """
        if fullname in sys.modules:
            return sys.modules[fullname]
        mod = fullname.split(".")[-1]
        mod_obj = types.ModuleType(mod, f"Module created to provide a context for {mod}")
        with open(os.path.join(os.path.dirname(__file__), mod + ".yml"), "r") as stream:
            try:
                # modules = FactoryLoader().load(yaml.load(stream, Loader=yaml.FullLoader))
                # NOTE: Commenting FullLoader method to pass security check, changing to use safe_load
                modules = FactoryLoader().load(yaml.safe_load(stream))
            except yaml.YAMLError as exc:
                raise ImportError(f"{exc}\n.{mod} is not loaded.")
        for key, value in modules.items():
            setattr(mod_obj, key, value)
        sys.modules[fullname] = mod_obj
        return mod_obj


sys.meta_path.insert(0, MetaPathFinder())  # type: ignore
