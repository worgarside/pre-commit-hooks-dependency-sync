install:
	poetry install --all-extras --sync

try-repo:
	git add . && cd ../very-slow-movie-player && git add . && pre-commit try-repo ../pre-commit-hooks-dependency-sync

vscode-shortcut-1:
	make try-repo
