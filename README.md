# Pre-Commit Hook Additional Dependencies Synchronizer

This hook compares your `poetry.lock` or `uv.lock` file with the additional
dependencies in `prek.toml`, `.pre-commit-config.yaml`, or
`.pre-commit-config.yml`. Dependencies found in the lockfile are pinned to that
version in the hook config.

## Usage

Add this hook to a pre-commit YAML config:

```yaml
  - repo: https://github.com/worgarside/pre-commit-hooks-dependency-sync
    rev: 1.0.1
    hooks:
      - id: sync-additional-dependencies
```

Or add it to `prek.toml`:

```toml
[[repos]]
repo = "https://github.com/worgarside/pre-commit-hooks-dependency-sync"
rev = "1.0.1"

[[repos.hooks]]
id = "sync-additional-dependencies"
```

When `--config-path` is omitted, config discovery follows prek's precedence:
`prek.toml`, `.pre-commit-config.yaml`, then `.pre-commit-config.yml`.

## Configuration Options

You can customize the behavior of the hook by passing arguments:

```yaml
  - repo: https://github.com/worgarside/pre-commit-hooks-dependency-sync
    rev: 1.0.1
    hooks:
      - id: sync-additional-dependencies
        args:
          - --exclude-packages
          - package-name-1
          - package-name-2
```

### Available Arguments

- `--config-path` / `-c`: Path to `prek.toml` or a pre-commit YAML config (default: discover using prek's precedence). The previous `--pch-config-path` name remains supported.
- `--hook-name` / `-n`: Optional hook name to limit dependency updates to a specific hook
- `--package-manager` / `-p`: Package manager to use (`poetry` or `uv`, default: `poetry`)
- `--lockfile-path` / `-l`: Path to lockfile (default: `<package-manager>.lock` in repo root)
- `--exclude-packages` / `-e`: One or more package names to exclude from synchronization

### Example: Exclude Specific Packages

If you want to prevent certain packages from being synchronized (e.g., to maintain a specific version):

```yaml
  - repo: https://github.com/worgarside/pre-commit-hooks-dependency-sync
    rev: 1.0.1
    hooks:
      - id: sync-additional-dependencies
        args:
          - --exclude-packages
          - mypy
          - ruff
```

### Example: Using with uv

```yaml
  - repo: https://github.com/worgarside/pre-commit-hooks-dependency-sync
    rev: 1.0.1
    hooks:
      - id: sync-additional-dependencies
        args:
          - --package-manager
          - uv
```

## Development

This project uses uv for dependency management and builds:

```shell
uv sync --locked
uv run sync-dependencies --package-manager uv --lockfile-path uv.lock
uv build
```
