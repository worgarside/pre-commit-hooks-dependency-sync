"""Synchronize pre-commit hooks' dependencies with Poetry's lockfile."""


from __future__ import annotations

from pathlib import Path

from pkg_resources import parse_requirements
from tomli import load
from yaml import dump, safe_load

REPO_PATH = Path().cwd()

POETRY_LOCKFILE = REPO_PATH / "poetry.lock"
PCH_CONFIG = REPO_PATH / ".pre-commit-config.yaml"


def main() -> None:
    with POETRY_LOCKFILE.open("rb") as poetry_lockfile:
        packages = load(poetry_lockfile).get("package", [])

    installed = {package["name"]: package["version"] for package in packages}

    with PCH_CONFIG.open("r") as pch_config:
        config = safe_load(pch_config)

    for repo in config["repos"]:
        for hook in repo.get("hooks", []):
            updates = {}

            for req in parse_requirements(hook.get("additional_dependencies", [])):
                if (
                    target_version := installed.get(req.key)
                ) and req.specifier != f"=={target_version}":
                    updates[req.key] = f"=={target_version}"

            if updates:
                hook["additional_dependencies"] = sorted(
                    [
                        x
                        for x in hook["additional_dependencies"]
                        if next(parse_requirements(x)).key not in updates
                    ]
                    + [f"{req}{version}" for req, version in updates.items()],
                    key=lambda x: next(parse_requirements(x)).name,
                )

    raw_yaml = dump(config, indent=2, sort_keys=False)

    pretty_yaml = "---\n" + raw_yaml.replace("\n- ", "\n\n- ")

    PCH_CONFIG.write_text(pretty_yaml)


if __name__ == "__main__":
    main()
