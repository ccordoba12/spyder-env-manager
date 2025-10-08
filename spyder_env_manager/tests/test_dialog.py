# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2022, Spyder Development Team and spyder-env-manager contributors
#
# Licensed under the terms of the MIT license
# ----------------------------------------------------------------------------

"""
Spyder Env Manager dialog tests.
"""

# Standard library imports
import logging
from pathlib import Path
from unittest.mock import Mock

# Third-party imports
import pytest
from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QMainWindow, QMessageBox

# Spyder imports
from spyder.config.manager import CONF

# Local imports
from spyder_env_manager.spyder.config import CONF_DEFAULTS
from spyder_env_manager.spyder.plugin import SpyderEnvManager
from spyder_env_manager.spyder.widgets.dialog import EnvManagerDialog
from spyder_env_manager.spyder.widgets.manager import (
    SpyderEnvManagerWidget,
    SpyderEnvManagerWidgetActions,
)
from spyder_env_manager.spyder.workers import EnvironmentManagerWorker

# Constants
OPERATION_TIMEOUT = 180000
IMPORT_FILE_PATH = str(
    Path(__file__).parents[2]
    / "external-deps"
    / "envs-manager"
    / "envs_manager"
    / "tests"
    / "env_files"
    / "pixi-files"
    / "pixi_export_env.zip"
)


# ---- Fixtures
# ------------------------------------------------------------------------
class MainMock(QMainWindow):
    def __init__(self):
        super().__init__()
        self.switcher = Mock()
        self.main = self
        self.resize(640, 480)

    def get_plugin(self, plugin_name, error=True):
        return Mock()


@pytest.fixture
def spyder_env_manager_conf(tmp_path, qtbot, monkeypatch):
    # Mocking mainwindow and get_config
    window = MainMock()
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

    # Setup plugin
    plugin = SpyderEnvManager(parent=window, configuration=CONF)
    manager = SpyderEnvManagerWidget(plugin.NAME, plugin)
    window.setCentralWidget(manager)
    manager.show()

    yield plugin

    manager.close()


@pytest.fixture
def env_manager_dialog(tmp_path, qtbot, monkeypatch):
    # Mocking mainwindow, get_config and CONF
    window = MainMock()
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

    # Setup plugin
    plugin = SpyderEnvManager(parent=window, configuration=Mock())
    manager = SpyderEnvManagerWidget(plugin.NAME, plugin)
    dialog = EnvManagerDialog(window, manager, plugin.get_name(), plugin.get_icon())
    dialog.show()

    yield dialog

    dialog.close()


# ---- Tests
# -------------------------------------------------------------------------------------
def test_initial_state(env_manager_dialog):
    """
    Check that actions and widgets have the correct state when initialized.
    """
    dialog = env_manager_dialog
    manager = env_manager_dialog._envs_manager
    new_env_action = manager.get_action(SpyderEnvManagerWidgetActions.NewEnvironment)
    import_action = manager.get_action(SpyderEnvManagerWidgetActions.ImportEnvironment)

    # Check for initial state (no envs)
    assert manager.stack_widget.currentWidget() == manager.new_env_widget
    assert manager._corner_widget.widgetForAction(new_env_action).width() == 0
    assert manager._corner_widget.widgetForAction(import_action).width() != 0

    assert dialog._button_next.isVisible()
    assert dialog._button_cancel.isVisible()

    assert not dialog._button_back.isVisible()
    assert not dialog._button_import.isVisible()
    assert not dialog._button_create.isVisible()


def test_environment_creation_and_deletion(env_manager_dialog, qtbot, caplog):
    """Test creating and deleting an environment."""
    caplog.set_level(logging.DEBUG)
    dialog = env_manager_dialog
    manager = env_manager_dialog._envs_manager

    assert dialog._button_next.isVisible()

    # Click next and ckeck we're displaying right widget
    dialog._button_next.clicked.emit()
    assert manager.stack_widget.currentWidget() == manager.edit_env_widget
    assert manager.edit_env_widget._empty_message.isVisible()

    # Check buttons state
    assert dialog._button_back.isVisible()
    assert not dialog._button_next.isVisible()
    assert dialog._button_create.isVisible()
    assert not dialog._button_create.isEnabled()
    assert manager.edit_env_widget._add_package_button.isEnabled()

    # Add a package
    manager.edit_env_widget._package_name.textbox.setText("numpy")
    manager.edit_env_widget._package_version.textbox.setText("2.1.0")
    manager.edit_env_widget._add_package_button.clicked.emit()

    # Check state after doing that
    assert not manager.edit_env_widget._empty_message.isVisible()
    assert dialog._button_create.isEnabled()
    assert not manager._spinner._isSpinning

    # Create env
    dialog._button_create.clicked.emit()

    # Check buttons state
    assert not dialog._button_create.isEnabled()
    assert not dialog._button_back.isEnabled()

    # Check widgets state
    assert manager._spinner._isSpinning
    assert not manager.edit_env_widget._package_name.textbox.isEnabled()
    assert not manager.edit_env_widget._package_version.textbox.isEnabled()
    assert not manager.edit_env_widget._add_package_button.isEnabled()
    assert not manager.edit_env_widget._packages_table.isEnabled()

    # Wait until the env is created. Packages that should be in the table are three:
    # Numpy, Python and Spyder-kernels
    qtbot.waitUntil(
        lambda: len(manager.edit_env_widget._packages_table.elements) == 3,
        timeout=OPERATION_TIMEOUT,
    )

    # Check buttons state
    assert not dialog._button_create.isVisible()
    assert dialog._button_cancel.text() == "Close"
    assert dialog._button_back.isEnabled()

    # Check widgets state
    assert not manager._spinner._isSpinning
    assert manager.edit_env_widget._package_name.textbox.isEnabled()
    assert manager.edit_env_widget._package_version.textbox.isEnabled()
    assert manager.edit_env_widget._add_package_button.isEnabled()
    assert manager.edit_env_widget._packages_table.isEnabled()

    # Click Back and check we display the right widget
    dialog._button_back.clicked.emit()
    assert manager.stack_widget.currentWidget() == manager.list_envs_widget

    # Check buttons state
    assert dialog._button_cancel.text() == "Close"
    assert not dialog._button_back.isVisible()

    # Check corner widgets state
    new_env_action = manager.get_action(SpyderEnvManagerWidgetActions.NewEnvironment)
    import_action = manager.get_action(SpyderEnvManagerWidgetActions.ImportEnvironment)
    assert manager._corner_widget.widgetForAction(new_env_action).width() != 0
    assert manager._corner_widget.widgetForAction(import_action).width() != 0

    # Check we're displaying the new env
    len(manager.list_envs_widget._table.elements) == 1
    env_element = manager.list_envs_widget._table.elements[0]
    assert "default" in env_element["title"]
    assert "Python 3.12" in env_element["title"]
    assert "pixi/envs/default" in env_element["description"]

    # Edit env to check its contents
    edit_button = env_element["widget"].layout().itemAt(2).widget()
    edit_button.clicked.emit()

    qtbot.waitUntil(
        lambda: manager.stack_widget.currentWidget() == manager.edit_env_widget,
        timeout=OPERATION_TIMEOUT,
    )

    # Check buttons state
    assert dialog._button_back.isVisible()
    assert manager._corner_widget.widgetForAction(new_env_action).width() == 0
    assert manager._corner_widget.widgetForAction(import_action).width() == 0

    # Check packages_table state
    qtbot.wait(1000)
    assert len(manager.edit_env_widget._packages_table.elements) == 3
    assert ["numpy", "python", "spyder-kernels"] == [
        package["title"] for package in manager.edit_env_widget._packages_table.elements
    ]

    # Return to list_envs_widget
    dialog._button_back.clicked.emit()
    qtbot.wait(1000)

    # Delete environment
    def handle_environment_deletion_dialog():
        message = manager.findChild(QMessageBox)
        button_yes = message.button(QMessageBox.Yes)
        button_yes.clicked.emit()

    QTimer.singleShot(2000, handle_environment_deletion_dialog)

    env_element_1 = manager.list_envs_widget._table.elements[0]
    delete_button = env_element_1["widget"].layout().itemAt(0).widget()
    delete_button.clicked.emit()

    # Check widgets state
    assert manager._spinner._isSpinning
    assert not manager.list_envs_widget._table.isEnabled()
    assert not manager.list_envs_widget._finder.isEnabled()

    # Since there are no more envs, we must display new_env_widget after the operation
    # has finished
    qtbot.waitUntil(
        lambda: manager.stack_widget.currentWidget() == manager.new_env_widget,
        timeout=OPERATION_TIMEOUT,
    )

    # Check widgets state
    assert not manager._spinner._isSpinning
    assert manager.list_envs_widget._table.isEnabled()
    assert manager.list_envs_widget._finder.isEnabled()
    assert manager.list_envs_widget._envs == {None: {}}
    assert dialog._button_next.isVisible()
    assert dialog._button_cancel.text() == "Cancel"


def test_environment_import(env_manager_dialog, qtbot, caplog):
    """Test importing an environment from a file."""
    caplog.set_level(logging.DEBUG)
    dialog = env_manager_dialog
    manager = env_manager_dialog._envs_manager
    import_action = manager.get_action(SpyderEnvManagerWidgetActions.ImportEnvironment)
    new_env_action = manager.get_action(SpyderEnvManagerWidgetActions.NewEnvironment)

    # Switch to import_env_widget
    import_action.triggered.emit()

    # Check widgets state
    assert manager.stack_widget.currentWidget() == manager.import_env_widget
    assert manager._corner_widget.widgetForAction(new_env_action).width() != 0
    assert manager._corner_widget.widgetForAction(import_action).width() == 0

    # Check buttons state
    assert dialog._button_import.isVisible()
    assert dialog._button_cancel.isVisible()

    assert not dialog._button_back.isVisible()
    assert not dialog._button_next.isVisible()
    assert not dialog._button_create.isVisible()

    # Add import file
    manager.import_env_widget.zip_file.textbox.setText(IMPORT_FILE_PATH)

    # Check env name is automatically set using the import file name
    qtbot.wait(500)
    assert manager.import_env_widget.env_name.textbox.text() == "pixi_export_env"

    # Import env
    dialog._button_import.clicked.emit()

    # Check widgets state
    assert manager._spinner._isSpinning
    assert not manager.import_env_widget.zip_file.textbox.isEnabled()
    assert not manager.import_env_widget.env_name.textbox.isEnabled()

    # Check buttons state
    assert not dialog._button_import.isEnabled()
    assert not dialog._button_cancel.isEnabled()

    # If everything goes well we should display list_envs_widget after the operation
    # has finished
    qtbot.waitUntil(
        lambda: manager.stack_widget.currentWidget() == manager.list_envs_widget,
        timeout=OPERATION_TIMEOUT,
    )

    # Check widgets state
    assert not manager._spinner._isSpinning
    assert manager._corner_widget.widgetForAction(new_env_action).width() != 0
    assert manager._corner_widget.widgetForAction(import_action).width() != 0

    # Check buttons state
    assert not dialog._button_import.isVisible()
    assert dialog._button_cancel.isEnabled()
    dialog._button_cancel.text() == "Close"

    # Check we're displaying the new env
    len(manager.list_envs_widget._table.elements) == 1
    env_element = manager.list_envs_widget._table.elements[0]
    assert "pixi_export_env" in env_element["title"]
    assert "Python 3.10.5" in env_element["title"]
    assert "pixi/envs/pixi_export_env" in env_element["description"]

    # Edit env to check its contents
    edit_button = env_element["widget"].layout().itemAt(2).widget()
    edit_button.clicked.emit()

    qtbot.waitUntil(
        lambda: manager.stack_widget.currentWidget() == manager.edit_env_widget,
        timeout=OPERATION_TIMEOUT,
    )

    # Check buttons state
    assert dialog._button_back.isVisible()

    # Check packages_table state
    qtbot.wait(1000)
    assert len(manager.edit_env_widget._packages_table.elements) == 3
    assert ["packaging", "python", "spyder-kernels"] == [
        package["title"] for package in manager.edit_env_widget._packages_table.elements
    ]

    # Return to list_envs_widget
    dialog._button_back.clicked.emit()

    # Go to import_env_widget and check its fields are cleared and enabled
    import_action.triggered.emit()

    assert manager.import_env_widget.zip_file.textbox.text() == ""
    assert manager.import_env_widget.zip_file.textbox.isEnabled()

    assert manager.import_env_widget.env_name.textbox.text() == ""
    assert manager.import_env_widget.env_name.textbox.isEnabled()
