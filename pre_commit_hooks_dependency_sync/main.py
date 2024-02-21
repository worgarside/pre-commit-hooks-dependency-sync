"""Synchronize pre-commit hooks' dependencies with Poetry's lockfile."""

from __future__ import annotations

import re
from pathlib import Path

from packaging.requirements import Requirement
from tomli import load
from yaml import safe_load

REPO_PATH = Path().cwd()

POETRY_LOCKFILE = REPO_PATH / "poetry.lock"
PCH_CONFIG = REPO_PATH / ".pre-commit-config.yaml"

ADD_DEP_PREFIX = r"(\s+-\s)"


def get_poetry_packages(lockfile: Path) -> dict[str, str]:
    """Get a dictionary of dependencies from the Poetry lockfile."""
    with lockfile.open("rb") as poetry_lockfile:
        packages = load(poetry_lockfile).get("package", [])

    return {package["name"]: package["version"] for package in packages}


def get_replacements() -> dict[str, str]:
    """Get a dictionary of dependencies to replace in the pre-commit config."""
    installed = get_poetry_packages(POETRY_LOCKFILE)

    with PCH_CONFIG.open("r") as pch_config:
        config = safe_load(pch_config)

    replacements = {}

    for repo in config["repos"]:
        for hook in repo.get("hooks", []):
            for req_str in hook.get("additional_dependencies", []):
                req = Requirement(req_str)

                repl_pattern = (
                    re.escape(req.name)
                    + (r"\[.+\]" if req.extras else "")
                    + re.escape(str(req.specifier))
                )

                if (
                    repl_pattern not in replacements
                    and (target_version := installed.get(req.name)) is not None
                    and req.specifier != f"=={target_version}"
                ):
                    replacements[repl_pattern] = (
                        req.name
                        + (f"[{','.join(req.extras)}]" if req.extras else "")
                        + f"=={target_version}"
                    )

    return replacements


def main() -> None:
    """Update the pre-commit config with the latest versions of dependencies."""
    with PCH_CONFIG.open("r") as f:
        lines = f.readlines()

    updated_lines = []
    apply_updates = False

    replacements = get_replacements()

    for line in lines:
        updated_line = line
        for repl_pattern, value in replacements.items():
            updated_line = re.sub(
                f"^{ADD_DEP_PREFIX}{repl_pattern}$",
                f"\\1{value}",
                updated_line,
            )

        apply_updates |= updated_line != line
        updated_lines.append(updated_line)

    if apply_updates:
        with PCH_CONFIG.open("w") as f:
            f.writelines(updated_lines)


if __name__ == "__main__":
    main()
