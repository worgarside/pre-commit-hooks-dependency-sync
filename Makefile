install:
	uv sync --locked --all-groups

try-repo:
	git add . && cd ../home-assistant-config-validator && git add . && uvx prek try-repo ../pre-commit-hooks-dependency-sync

vscode-shortcut-1:
	make try-repo
