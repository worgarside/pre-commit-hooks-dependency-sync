"""Synchronize pre-commit hooks' dependencies with Poetry's lockfile."""

from __future__ import annotations

import re
from argparse import ArgumentParser
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from tomli import load
from yaml import safe_load

REPO_PATH = Path().cwd()

ADD_DEP_PREFIX = r"(\s+-\s)"


def get_poetry_packages(lockfile: Path) -> dict[str, str]:
    """Get a dictionary of dependencies from the Poetry lockfile."""
    with lockfile.open("rb") as poetry_lockfile:
        packages = load(poetry_lockfile).get("package", [])

    return {package["name"].casefold(): package["version"] for package in packages}


def get_replacements(lockfile: Path, pch_config: Path) -> dict[str, str]:
    """Get a dictionary of dependencies to replace in the pre-commit config."""
    installed = get_poetry_packages(lockfile)

    with pch_config.open("r") as fin:
        config = safe_load(fin)

    replacements = {}

    for repo in config["repos"]:
        for hook in repo.get("hooks", []):
            for req_str in hook.get("additional_dependencies", []):
                try:
                    req = Requirement(req_str)
                except InvalidRequirement:
                    if req_str.startswith("git+"):
                        # Skip git dependencies
                        continue
                    raise

                repl_pattern = (
                    re.escape(req.name)
                    + (r"\[.+\]" if req.extras else "")
                    + re.escape(str(req.specifier))
                )

                if (
                    repl_pattern not in replacements
                    and (target_version := installed.get(req.name.casefold())) is not None
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
        "-l",
        "--lockfile-path",
        type=Path,
        required=False,
        help="Path to poetry.lock",
        default=REPO_PATH / "poetry.lock",
    )

    args, _ = parser.parse_known_args()

    lockfile: Path = args.lockfile_path
    pch_config: Path = args.pch_config_path

    with pch_config.open("r") as f:
        lines = f.readlines()

    updated_lines = []
    apply_updates = False

    replacements = get_replacements(lockfile, pch_config)

    for line in lines:
        updated_line = line
        for repl_pattern, value in replacements.items():
            updated_line = re.sub(
                f"^{ADD_DEP_PREFIX}{repl_pattern}$",
                f"\\1{value}",
                updated_line,
                flags=re.IGNORECASE,
            )

        apply_updates |= updated_line != line
        updated_lines.append(updated_line)

    if apply_updates:
        with pch_config.open("w") as f:
            f.writelines(updated_lines)


if __name__ == "__main__":
    main()
