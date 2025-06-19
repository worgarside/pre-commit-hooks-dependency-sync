"""Synchronize pre-commit hooks' dependencies with Poetry's lockfile."""

from __future__ import annotations

import re
from argparse import ArgumentParser
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from ruamel.yaml import YAML
from tomli import load

YAML_LOADER = YAML(typ="rt")
YAML_LOADER.explicit_start = True
YAML_LOADER.preserve_quotes = True
YAML_LOADER.indent(mapping=2, sequence=4, offset=2)
YAML_LOADER.width = 4096

EQUIV_CHARS = re.compile(r"[-_.]")
"""Characters that are considered equivalent within package names.

Example:
    case 1: "package-name" == "package_name"
    case 2: "real-package_name" == "real_package_name"
"""

REPO_PATH = Path().cwd()


def get_poetry_packages(lockfile: Path) -> dict[str, str]:
    """Get a dictionary of dependencies from the Poetry lockfile."""
    with lockfile.open("rb") as poetry_lockfile:
        # converts toml to dicts
        packages = load(poetry_lockfile).get("package", [])

    return {package["name"]: package["version"] for package in packages}


def get_uv_packages(lockfile: Path) -> dict[str, str]:
    """Get a dictionary of dependencies from the uv lockfile."""
    with lockfile.open("rb") as uv_lockfile:
        # converts toml to dicts
        packages = load(uv_lockfile).get("package", [])

    return {
        package["name"]: package["version"]
        for package in packages
        # there are cases in which the package does not have a version
        if "version" in package and "name" in package
    }


def get_installed_packages(lockfile: Path, package_manager: str) -> dict[str, str]:
    """Get a dictionary of dependencies from the lockfile."""
    if package_manager == "poetry":
        return get_poetry_packages(lockfile)

    if package_manager == "uv":
        return get_uv_packages(lockfile)

    raise NotImplementedError(f"Package manager {package_manager!r} not implemented")


def main() -> None:
    """Update the pre-commit config with the latest versions of dependencies."""
    parser = ArgumentParser()
    parser.add_argument(
        "-c",
        "--pch-config-path",
        type=Path,
        required=False,
        help="Path to .pre-commit-config.yaml",
        default=REPO_PATH / ".pre-commit-config.yaml",
    )
    parser.add_argument(
        "-n",
        "--hook-name",
        type=str,
        required=False,
        help="Optional hook name to limit dependency updates to",
        default=None,
    )
    parser.add_argument(
        "-p",
        "--package-manager",
        type=str,
        required=False,
        help="Package manager to use for dependency management",
        default="poetry",
        choices=["poetry", "uv"],
    )

    # avoids having a manager-specific default path
    default_path = "<repo path>/<package manager>.lock"

    parser.add_argument(
        "-l",
        "--lockfile-path",
        type=Path,
        required=False,
        help="Path to lockfile",
        default=default_path,
    )

    args, _ = parser.parse_known_args()

    pch_config: Path = args.pch_config_path
    hook_name: str | None = args.hook_name
    package_manager: str = args.package_manager

    if str(args.lockfile_path) == default_path:
        lockfile: Path = REPO_PATH / f"{package_manager}.lock"
    else:
        lockfile = args.lockfile_path

    installed = get_installed_packages(lockfile, package_manager)

    with pch_config.open("r") as fin:
        config = YAML_LOADER.load(fin)

    for repo in config["repos"]:
        for hook in repo.get("hooks", []):
            if hook_name and hook.get("name") != hook_name:
                continue

            for i, req_str in enumerate(hook.get("additional_dependencies", [])):
                try:
                    req = Requirement(req_str)
                except InvalidRequirement:
                    if req_str.startswith("git+"):
                        # Skip git dependencies
                        continue
                    raise

                for installed_req in installed:
                    if EQUIV_CHARS.sub(
                        " ",
                        installed_req.casefold(),
                    ) == EQUIV_CHARS.sub(
                        " ",
                        req.name.casefold(),
                    ):
                        target_version = installed[installed_req]
                        break
                else:
                    continue

                if req.specifier != f"=={target_version}":
                    hook["additional_dependencies"][i] = (
                        installed_req
                        + (f"[{','.join(sorted(req.extras))}]" if req.extras else "")
                        + f"=={target_version}"
                    )

    with pch_config.open("w") as fout:
        YAML_LOADER.dump(config, fout)


if __name__ == "__main__":
    main()
