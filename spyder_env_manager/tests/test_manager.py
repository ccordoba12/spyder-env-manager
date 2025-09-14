# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2022, Spyder Development Team and spyder-env-manager contributors
#
# Licensed under the terms of the MIT license
# ----------------------------------------------------------------------------
"""
Spyder Env Manager main widget tests.
"""
# Local imports
from spyder_env_manager.spyder.config import CONF_DEFAULTS, CONF_SECTION
from spyder_env_manager.spyder.widgets.manager import SpyderEnvManagerWidget
from spyder_env_manager.spyder.workers import EnvironmentManagerWorker


def test_manager(qtbot, tmp_path, monkeypatch):
    """Create widget and show it."""
    backends_root_path = tmp_path / "backends"
    backends_root_path.mkdir(parents=True)

    def get_conf(self, option, default=None, section=None):
        if option == "environments_path":
            return str(backends_root_path)
        else:
            try:
                _, config_default_values = CONF_DEFAULTS[0]
                return config_default_values[option]
            except KeyError:
                return None

    monkeypatch.setattr(SpyderEnvManagerWidget, "get_conf", get_conf)
    monkeypatch.setattr(EnvironmentManagerWorker, "get_conf", get_conf)

    SpyderEnvManagerWidget.CONF_SECTION = CONF_SECTION
    widget = SpyderEnvManagerWidget(CONF_SECTION, None)
    widget.show()
