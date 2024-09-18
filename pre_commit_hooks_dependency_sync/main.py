"""Synchronize pre-commit hooks' dependencies with Poetry's lockfile."""

from __future__ import annotations

from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from ruamel.yaml import YAML
from tomli import load

YAML_LOADER = YAML(typ="rt")
YAML_LOADER.explicit_start = True
YAML_LOADER.preserve_quotes = True
YAML_LOADER.indent(mapping=2, sequence=4, offset=2)
YAML_LOADER.width = 4096

REPO_PATH = Path().cwd()

POETRY_LOCKFILE = REPO_PATH / "poetry.lock"
PCH_CONFIG = REPO_PATH / ".pre-commit-config.yaml"

ADD_DEP_PREFIX = r"(\s+-\s)"


def get_poetry_packages(lockfile: Path) -> dict[str, str]:
    """Get a dictionary of dependencies from the Poetry lockfile."""
    with lockfile.open("rb") as poetry_lockfile:
        packages = load(poetry_lockfile).get("package", [])

    return {package["name"].casefold(): package["version"] for package in packages}


def main() -> None:
    """Update the pre-commit config with the latest versions of dependencies."""
    installed = get_poetry_packages(POETRY_LOCKFILE)

    with PCH_CONFIG.open("r") as pch_config:
        config = YAML_LOADER.load(pch_config)

    for repo in config["repos"]:
        for hook in repo.get("hooks", []):
            for i, req_str in enumerate(hook.get("additional_dependencies", [])):
                try:
                    req = Requirement(req_str)
                except InvalidRequirement:
                    if req_str.startswith("git+"):
                        # Skip git dependencies
                        continue
                    raise

                if (
                    target_version := installed.get(req.name.casefold())
                ) is not None and req.specifier != f"=={target_version}":
                    hook["additional_dependencies"][i] = (
                        req.name
                        + (f"[{','.join(req.extras)}]" if req.extras else "")
                        + f"=={target_version}"
                    )

    YAML_LOADER.dump(config, PCH_CONFIG)


if __name__ == "__main__":
    main()
