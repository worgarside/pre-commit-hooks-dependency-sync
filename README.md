# Pre-Commit Hook Additional Dependencies Synchronizer

This is a simple Pre-Commit Hook that will compare your `poetry.lock` or `uv.lock` file with the additional dependencies included in `.pre-commit-config.yaml`. Any additional dependencies which are found in the lockfile will be pinned to that version within the PCH config.

## Usage

Add this pre-commit hook to your project by adding the following to your `.pre-commit-config.yaml`:

```yaml
  - repo: https://github.com/worgarside/pre-commit-hooks-dependency-sync
    rev: 1.0.1
    hooks:
      - id: sync-additional-dependencies
```

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

- `--pch-config-path` / `-c`: Path to `.pre-commit-config.yaml` (default: `.pre-commit-config.yaml` in repo root)
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
