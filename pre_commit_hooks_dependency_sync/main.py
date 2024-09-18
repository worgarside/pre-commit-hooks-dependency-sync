"""Synchronize pre-commit hooks' dependencies with Poetry's lockfile."""

from __future__ import annotations

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

REPO_PATH = Path().cwd()

ADD_DEP_PREFIX = r"(\s+-\s)"


def get_poetry_packages(lockfile: Path) -> dict[str, str]:
    """Get a dictionary of dependencies from the Poetry lockfile."""
    with lockfile.open("rb") as poetry_lockfile:
        packages = load(poetry_lockfile).get("package", [])

    return {package["name"].casefold(): package["version"] for package in packages}


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

    installed = get_poetry_packages(lockfile)

    with pch_config.open("r") as fin:
        config = YAML_LOADER.load(fin)

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

    with pch_config.open("w") as fout:
        YAML_LOADER.dump(config, fout)


if __name__ == "__main__":
    main()
