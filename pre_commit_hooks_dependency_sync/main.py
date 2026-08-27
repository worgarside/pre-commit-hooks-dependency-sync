"""Synchronize pre-commit hooks' dependencies with a lockfile."""

from __future__ import annotations

import re
from argparse import ArgumentParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from packaging.requirements import InvalidRequirement, Requirement
from ruamel.yaml import YAML
from tomli import load
from tomlkit import dump as dump_toml
from tomlkit import load as load_toml

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
CONFIG_FILENAMES = ("prek.toml", ".pre-commit-config.yaml", ".pre-commit-config.yml")


class HookConfigNotFoundError(FileNotFoundError):
    """Raised when config discovery cannot find a supported file."""

    def __init__(self, filenames: tuple[str, ...]) -> None:
        """Initialize the error with the supported filenames."""
        supported = ", ".join(filenames)
        super().__init__(f"No hook config found; expected one of: {supported}")


class UnsupportedHookConfigError(ValueError):
    """Raised when a hook config has an unsupported extension."""

    def __init__(self, config_path: Path) -> None:
        """Initialize the error with the unsupported path."""
        super().__init__(f"Unsupported hook config format: {config_path}")


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


def get_poetry_git_sources(lockfile: Path) -> dict[str, str]:
    """Get git dependency sources from the Poetry lockfile."""
    with lockfile.open("rb") as poetry_lockfile:
        packages = load(poetry_lockfile).get("package", [])

    git_sources: dict[str, str] = {}
    for package in packages:
        source = package.get("source", {})
        if source.get("type") != "git":
            continue

        url = source.get("url")
        reference = source.get("resolved_reference") or source.get("reference")
        if not url:
            continue

        git_sources[package["name"]] = (
            f"git+{url}@{reference}" if reference else f"git+{url}"
        )

    return git_sources


def get_uv_git_sources(lockfile: Path) -> dict[str, str]:
    """Get git dependency sources from the uv lockfile."""
    with lockfile.open("rb") as uv_lockfile:
        packages = load(uv_lockfile).get("package", [])

    git_sources: dict[str, str] = {}
    for package in packages:
        source = package.get("source", {})
        git_url = source.get("git")
        if not git_url:
            continue

        parsed = urlsplit(git_url)
        ref = parsed.fragment or parse_qs(parsed.query).get("rev", [None])[0]
        query = parse_qs(parsed.query)
        query.pop("rev", None)
        query_string = urlencode(query, doseq=True) if query else ""
        base_url = urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, query_string, ""),
        )

        git_sources[package["name"]] = (
            f"git+{base_url}@{ref}" if ref else f"git+{base_url}"
        )

    return git_sources


def get_installed_packages(lockfile: Path, package_manager: str) -> dict[str, str]:
    """Get a dictionary of dependencies from the lockfile."""
    if package_manager == "poetry":
        return get_poetry_packages(lockfile)

    if package_manager == "uv":
        return get_uv_packages(lockfile)

    raise NotImplementedError(f"Package manager {package_manager!r} not implemented")


def get_git_sources(lockfile: Path, package_manager: str) -> dict[str, str]:
    """Get git dependency sources from the lockfile."""
    if package_manager == "poetry":
        return get_poetry_git_sources(lockfile)

    if package_manager == "uv":
        return get_uv_git_sources(lockfile)

    raise NotImplementedError(f"Package manager {package_manager!r} not implemented")


def find_dependency_key(name: str, available: dict[str, str]) -> str | None:
    """Find matching key in a dependency map using normalized names."""
    normalized_name = EQUIV_CHARS.sub(" ", name.casefold())
    for candidate in available:
        if EQUIV_CHARS.sub(" ", candidate.casefold()) == normalized_name:
            return candidate

    return None


def resolve_config_path(
    config_path: Path | None,
    repo_path: Path | None = None,
) -> Path:
    """Resolve an explicit config path or discover one using prek precedence."""
    if config_path is not None:
        return config_path

    root = repo_path or REPO_PATH
    for filename in CONFIG_FILENAMES:
        candidate = root / filename
        if candidate.is_file():
            return candidate

    raise HookConfigNotFoundError(CONFIG_FILENAMES)


def load_config(config_path: Path) -> Any:
    """Load a supported hook config while preserving formatting metadata."""
    if config_path.suffix == ".toml":
        with config_path.open("r", encoding="utf-8") as config_file:
            return load_toml(config_file)

    if config_path.suffix in {".yaml", ".yml"}:
        with config_path.open("r", encoding="utf-8") as config_file:
            return YAML_LOADER.load(config_file)

    raise UnsupportedHookConfigError(config_path)


def dump_config(config_path: Path, config: Any) -> None:
    """Write a hook config in the format selected by its path."""
    if config_path.suffix == ".toml":
        with config_path.open("w", encoding="utf-8") as config_file:
            dump_toml(config, config_file)
        return

    if config_path.suffix in {".yaml", ".yml"}:
        with config_path.open("w", encoding="utf-8") as config_file:
            YAML_LOADER.dump(config, config_file)
        return

    raise UnsupportedHookConfigError(config_path)


def sync_dependencies(
    config: Any,
    installed: dict[str, str],
    git_sources: dict[str, str],
    hook_name: str | None,
    exclude_packages: list[str],
) -> None:
    """Synchronize additional dependencies in a parsed hook config."""
    normalized_excludes = {
        EQUIV_CHARS.sub(" ", package.casefold()) for package in exclude_packages
    }

    for repo in config["repos"]:
        for hook in repo.get("hooks", []):
            if hook_name and hook.get("name") != hook_name:
                continue

            for index, requirement_string in enumerate(
                hook.get("additional_dependencies", []),
            ):
                try:
                    requirement = Requirement(requirement_string)
                except InvalidRequirement:
                    if requirement_string.startswith("git+"):
                        continue
                    raise

                normalized_name = EQUIV_CHARS.sub(" ", requirement.name.casefold())
                if normalized_name in normalized_excludes:
                    continue

                if requirement.url:
                    matched_git = find_dependency_key(requirement.name, git_sources)
                    if not matched_git:
                        continue

                    expected = (
                        matched_git
                        + (
                            f"[{','.join(sorted(requirement.extras))}]"
                            if requirement.extras
                            else ""
                        )
                        + f" @ {git_sources[matched_git]}"
                    )
                    if requirement_string != expected:
                        hook["additional_dependencies"][index] = expected
                    continue

                matched_installed = find_dependency_key(requirement.name, installed)
                if not matched_installed:
                    continue

                target_version = installed[matched_installed]
                if requirement.specifier != f"=={target_version}":
                    hook["additional_dependencies"][index] = (
                        matched_installed
                        + (
                            f"[{','.join(sorted(requirement.extras))}]"
                            if requirement.extras
                            else ""
                        )
                        + f"=={target_version}"
                    )


def main() -> None:
    """Update the pre-commit config with the latest versions of dependencies."""
    parser = ArgumentParser()
    parser.add_argument(
        "-c",
        "--config-path",
        "--pch-config-path",
        type=Path,
        required=False,
        help="Path to prek.toml or a pre-commit YAML config",
        default=None,
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
    parser.add_argument(
        "-e",
        "--exclude-packages",
        type=str,
        nargs="+",
        required=False,
        help="Package names to exclude from synchronization",
        default=[],
    )

    args, _ = parser.parse_known_args()

    config_path = resolve_config_path(args.config_path)
    hook_name: str | None = args.hook_name
    package_manager: str = args.package_manager
    exclude_packages: list[str] = args.exclude_packages

    if str(args.lockfile_path) == default_path:
        lockfile: Path = REPO_PATH / f"{package_manager}.lock"
    else:
        lockfile = args.lockfile_path

    installed = get_installed_packages(lockfile, package_manager)
    git_sources = get_git_sources(lockfile, package_manager)

    config = load_config(config_path)
    sync_dependencies(
        config,
        installed,
        git_sources,
        hook_name,
        exclude_packages,
    )
    dump_config(config_path, config)


if __name__ == "__main__":
    main()
