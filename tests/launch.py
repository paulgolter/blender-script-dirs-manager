import argparse
import logging
import os
import platform
import subprocess
from pathlib import Path

logger = logging.getLogger("launch")

logging.basicConfig(level=logging.INFO)


def get_blender_default_installation_path(blender_version: str = "4.2") -> Path:
    system = platform.system()
    if system == "Windows":
        return Path(f"C:/Program Files/Blender Foundation/Blender {blender_version}/blender.exe")
    elif system == "Linux":
        return Path(f"/usr/local/blender-{blender_version}/blender")
    elif system == "Darwin":  # macOs
        return Path("/Applications/Blender.app/Contents/MacOS/Blender")
    else:
        raise ValueError(f"Unsupported operating system: {system}")


def get_studio_path() -> Path:
    return Path(__file__).parent / "script_dirs" / "studio" / "script_dir"


def get_project_path(project_name: str) -> Path:
    return Path(__file__).parent / "script_dirs" / project_name / "script_dir"


def launch() -> None:
    parser = argparse.ArgumentParser(description="Launch script")
    parser.add_argument(
        "--project",
        type=str,
        choices=["project_01", "project_02"],
        required=True,
        help="Specify the project name: project_01 or project_02",
    )
    parser.add_argument(
        "--blender",
        type=str,
        default="",
        help="Specify the blender installation path. If not specified, the default installation path will be used.",
    )

    # Args
    args = parser.parse_args()
    blender_path = Path(args.blender)
    if not args.blender:
        blender_path = get_blender_default_installation_path()

    if not blender_path.exists():
        raise FileNotFoundError(f"Blender executable not found: {blender_path}")

    # Launch
    env = os.environ.copy()
    env["PATH"] = str(blender_path.parent) + os.pathsep + env.get("PATH", "")
    studio_path = get_studio_path()
    project_path = get_project_path(args.project)

    blender_scripts_dir = os.pathsep.join([str(studio_path), str(project_path)])
    env["BLENDER_SCRIPT_DIRS"] = blender_scripts_dir

    logger.info("Launching Blender: %s", blender_path)
    logger.info("Project: %s", args.project)

    cmd_list = [str(blender_path), "--python", str(Path(__file__).parent.parent / "manage_script_dirs.py")]

    subprocess.run(cmd_list, env=env)


if __name__ == "__main__":
    launch()
