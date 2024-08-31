"""Manages the loading of add-ons and executing startup scripts in Blender from arbitrary script directories.

This script processes the non-blender env variable BLENDER_SCRIPT_DIRS.

The env variable should contain a list of directories separated by the os.pathsep character.

This script will add all directories in the env variable to the blender script directories in the user preferences.

If the script directory was not already present, it will execute all python files in the startup sub-directory

as well as enable all add-ons in the add-ons sub-directory.

Before adding the provided script directories it will remove all script directories that are not present anymore in the env variable.

It will also disable all add-ons that were associated with removed script directories.

If you are unsure what the directory layout of a blender script directory is, refer to this link:
https://docs.blender.org/manual/en/latest/advanced/blender_directory_layout.html#path-layout

To use this script:

01. Set the env variable to a list of script directories separated by the os.pathsep character.
set BLENDER_SCRIPT_DIRS=/studio/blender/scripts:/project1/blender/scripts

02. Start blender with the script as an argument.
blender --python <PATH_TO_THIS_SCRIPT>
"""

import importlib
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Iterable

import addon_utils
import bpy

SCRIPT_DIR_ITEM_NAME = "_script_dirs_manager"

logger = logging.getLogger("script_dirs")


def get_script_dirs_from_env() -> list[Path]:
    script_paths: list[Path] = []
    for p in os.environ["BLENDER_SCRIPT_DIRS"].split(os.pathsep):
        path = Path(p)
        if path not in script_paths:
            script_paths.append(path)
    return script_paths


def get_blender_prefs_script_dirs() -> bpy.types.bpy_prop_collection:
    return bpy.context.preferences.filepaths.script_directories


def disable_addon(module_name: str) -> None:
    logger.info("Disable addon: %s", module_name)
    bpy.ops.preferences.addon_disable(module=module_name)


def remove_path_from_sys(path: Path) -> None:
    sys_paths = [Path(p) for p in sys.path]
    try:
        idx = sys_paths.index(path)
    except ValueError:
        return
    else:
        sys.path.pop(idx)


def add_path_to_sys(path: Path) -> None:
    bpy.utils._sys_path_ensure_append(str(path))  # type: ignore


def get_script_dir_sys_paths(script_dir: Path) -> list[Path]:
    paths = [
        script_dir / "modules",
        script_dir / "startup",
        script_dir / "addons",
        # script_dir / "addons" / "modules", # Seems to be not supported by blender even doc says so?
    ]
    return paths


def add_script_dir_sys_paths(script_dir: Path) -> None:
    for path in get_script_dir_sys_paths(script_dir):
        add_path_to_sys(path)


def remove_script_dir_sys_paths(script_dir: Path) -> None:
    for path in get_script_dir_sys_paths(script_dir):
        remove_path_from_sys(path)


def enable_addon(module_name: str) -> None:
    enabled, loaded = addon_utils.check(module_name)

    if enabled and loaded:
        logger.info("Addon already loaded: %s", module_name)
        return

    # This is an add-on that is missing
    # if enabled and not loaded:

    # This loads the add-on but does not enable it in the preferences
    # https://projects.blender.org/blender/blender/issues/126029
    # addon_utils.enable(MODULE_NAME)

    logger.info("Enable addon: %s", module_name)
    bpy.ops.preferences.addon_enable(module=module_name)


def script_dirs_get_all_managed_items() -> list[bpy.types.ScriptDirectory]:
    script_dirs = get_blender_prefs_script_dirs()
    managed_items = []
    for name, item in script_dirs.items():
        if name.lower().startswith(SCRIPT_DIR_ITEM_NAME):
            managed_items.append(item)
    return managed_items


def script_dirs_remove_all_managed_items() -> list[bpy.types.ScriptDirectory]:
    script_dirs = get_blender_prefs_script_dirs()
    items_to_remove = script_dirs_get_all_managed_items()
    for item in items_to_remove:
        script_dirs.remove(item)  # type: ignore
    return items_to_remove


def script_dir_enable_addons(script_dir: Path) -> None:
    addon_dir = script_dir / "addons"
    if not addon_dir.exists():
        return
    for module_name, module_path in bpy.path.module_names(str(addon_dir)):  # type: ignore
        enable_addon(module_name)  # type: ignore


def script_dir_exec_startup_scripts(script_dir: Path) -> None:
    startup_dir = script_dir / "startup"
    if not startup_dir.exists():
        return
    for python_file in startup_dir.glob("*.py"):
        logger.info("Executing startup: %s", python_file)
        module = importlib.import_module(python_file.stem)
        register_callable = getattr(module, "register", None)

        if register_callable is None or not inspect.isfunction(register_callable):
            logger.warning("No register function found in: %s", python_file)
            continue

        register_callable()  # type: ignore


def script_dir_is_installed(script_dir: Path) -> bool:
    script_dirs = get_blender_prefs_script_dirs()
    for name, item in script_dirs.items():
        if Path(item.directory) == script_dir:
            return True
    return False


def remove_unlisted_script_dirs(scripts_paths: Iterable[Path]) -> None:
    script_dirs = get_blender_prefs_script_dirs()
    items_remove: list[bpy.types.ScriptDirectory] = []
    addon_names_disable: set[str] = set()

    for item in script_dirs_get_all_managed_items():
        dir_path = Path(item.directory)
        if dir_path not in scripts_paths:
            items_remove.append(item)
            addons_path = dir_path / "addons"
            module_data: tuple[str, str] = bpy.path.module_names(str(addons_path))  # type: ignore
            addon_names = [module_name for module_name, _ in module_data]  # type: ignore
            addon_names_disable.update(addon_names)

    for name in addon_names_disable:
        disable_addon(name)

    for item in items_remove:
        dir_path = Path(item.directory)
        script_dirs.remove(item)  # type: ignore
        remove_script_dir_sys_paths(dir_path)

    # Remove from sys path
    bpy.ops.extensions.repo_refresh_all()


def add_missing_script_dirs(scripts_paths: Iterable[Path]) -> None:
    script_dirs = get_blender_prefs_script_dirs()
    items_new: list[bpy.types.ScriptDirectory] = []
    for dir_path in scripts_paths:
        if not dir_path.exists():
            logger.warning("Script dir does not exist: %s", dir_path)
            continue

        # If a script dir was aleady added, we don't handle it
        # that way users can enable-disable add-ons on top of this
        if script_dir_is_installed(dir_path):
            # logger.debug("Script dir already installed: %s", dir_path)
            continue

        item = script_dirs.new()  # type: ignore
        item.name = SCRIPT_DIR_ITEM_NAME
        item.directory = dir_path.as_posix()
        items_new.append(item)

        # print("Added script dir: ", item.directory)

    bpy.ops.extensions.repo_refresh_all()

    for item in items_new:
        dir_path = Path(item.directory)
        add_script_dir_sys_paths(dir_path)
        script_dir_exec_startup_scripts(dir_path)
        script_dir_enable_addons(dir_path)


def report_as_error(text: str) -> None:
    def callback(self: bpy.types.Menu, context: bpy.types.Context) -> None:
        self.layout.label(text=text)

    bpy.context.window_manager.popup_menu(callback, title="Error", icon="ERROR")


def main() -> None:
    # Script directories are only available since Blender 4.0
    version_major = bpy.app.version[0]
    if version_major < 4:
        text = "Script directories require Blender 4.0 or newer"
        logger.error(text)
        if not bpy.app.background:
            report_as_error(text)
        return

    script_dirs = get_script_dirs_from_env()
    remove_unlisted_script_dirs(script_dirs)
    add_missing_script_dirs(script_dirs)

    bpy.ops.wm.save_userpref()


if __name__ == "__main__":
    # If we immediatly execeute on startup, we get access error on blender context
    bpy.app.timers.register(main)
