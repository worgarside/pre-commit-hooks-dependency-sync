# Pre-Commit Hook Additional Dependencies Synchronizer

This is a simple Pre-Commit Hook that will compare your `poetry.lock` file with the additional dependencies included in `.pre-commit-config.yaml`. Any additional dependencies which are found in the Poetry lockfile will be pinned to that version within the PCH config.

## Usage

Add this pre-commit hook to your project by adding the following to your `.pre-commit-config.yaml`:

```yaml
  - repo: https://github.com/worgarside/pre-commit-hooks-dependency-sync
    rev: 1.0.1
    hooks:
      - id: sync-additional-dependencies
```
