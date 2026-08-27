"""Tests for dependency synchronization across hook config formats."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pre_commit_hooks_dependency_sync.main import (
    HookConfigNotFoundError,
    dump_config,
    load_config,
    main,
    resolve_config_path,
    sync_dependencies,
)


class ConfigTests(unittest.TestCase):
    """Verify prek and pre-commit configuration handling."""

    def test_discovers_config_using_prek_precedence(self) -> None:
        """Prefer prek TOML when more than one supported config is present."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            yaml_path = root / ".pre-commit-config.yaml"
            toml_path = root / "prek.toml"
            yaml_path.touch()
            toml_path.touch()

            assert resolve_config_path(None, root) == toml_path

    def test_missing_config_has_actionable_error(self) -> None:
        """List supported filenames when config discovery fails."""
        with (
            TemporaryDirectory() as directory,
            self.assertRaisesRegex(HookConfigNotFoundError, r"prek\.toml"),
        ):
            resolve_config_path(None, Path(directory))

    def test_round_trips_and_updates_prek_toml(self) -> None:
        """Update TOML dependencies without discarding comments."""
        with TemporaryDirectory() as directory:
            config_path = Path(directory) / "prek.toml"
            config_path.write_text(
                """# retained comment
[[repos]]
repo = "local"

[[repos.hooks]]
id = "lint"
additional_dependencies = ["Example_Package>=1", "ignored==1"]
""",
                encoding="utf-8",
            )

            config = load_config(config_path)
            sync_dependencies(
                config,
                {"example-package": "2.0", "ignored": "3.0"},
                {},
                None,
                ["ignored"],
            )
            dump_config(config_path, config)

            result = config_path.read_text(encoding="utf-8")
            assert "# retained comment" in result
            assert '"example-package==2.0"' in result
            assert '"ignored==1"' in result

    def test_legacy_config_argument_still_works(self) -> None:
        """Retain the original long option while adding the generic name."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / ".pre-commit-config.yaml"
            lockfile_path = root / "poetry.lock"
            config_path.write_text(
                """repos:
  - repo: local
    hooks:
      - id: lint
        additional_dependencies:
          - package>=1
""",
                encoding="utf-8",
            )
            lockfile_path.write_text(
                """[[package]]
name = "package"
version = "2.0"
""",
                encoding="utf-8",
            )

            argv = [
                "sync-dependencies",
                "--pch-config-path",
                str(config_path),
                "--lockfile-path",
                str(lockfile_path),
            ]
            with patch.object(sys, "argv", argv):
                main()

            assert "package==2.0" in config_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
