"""Synchronize pre-commit hooks' dependencies with Poetry's lockfile."""


from __future__ import annotations

import re
from pathlib import Path

from pkg_resources import parse_requirements
from tomli import load
from yaml import safe_load

REPO_PATH = Path().cwd()

POETRY_LOCKFILE = REPO_PATH / "poetry.lock"
PCH_CONFIG = REPO_PATH / ".pre-commit-config.yaml"

ADD_DEP_PREFIX = r"(\s+-\s)"


def get_replacements() -> dict[str, str]:
    """Get a dictionary of dependencies to replace in the pre-commit config."""
    with POETRY_LOCKFILE.open("rb") as poetry_lockfile:
        packages = load(poetry_lockfile).get("package", [])

    installed = {package["name"]: package["version"] for package in packages}

    with PCH_CONFIG.open("r") as pch_config:
        config = safe_load(pch_config)

    replacements = {}

    for repo in config["repos"]:
        for hook in repo.get("hooks", []):
            for req in parse_requirements(hook.get("additional_dependencies", [])):
                if (
                    target_version := installed.get(req.key)
                ) and req.specifier != f"=={target_version}":
                    replacements[
                        f"{req.key}{req.specifier}"
                    ] = f"{req.key}=={target_version}"

    return replacements


def main() -> None:
    """Update the pre-commit config with the latest versions of dependencies."""
    with PCH_CONFIG.open("r") as f:
        lines = f.readlines()

    updated_lines = []
    apply_updates = False

    for line in lines:
        updated_line = line
        for key, value in get_replacements().items():
            updated_line = re.sub(
                f"^{ADD_DEP_PREFIX}{re.escape(key)}$", f"\\1{value}", updated_line
            )

        apply_updates |= updated_line != line
        updated_lines.append(updated_line)

    if apply_updates:
        with PCH_CONFIG.open("w") as f:
            f.writelines(updated_lines)


if __name__ == "__main__":
    main()
