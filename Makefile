all: generate
PY_FILES := $(shell find . -type f -regex ".*py" -print)


install:
	poetry install || true

lint: install
	poetry run pylint $(PY_FILES)
	poetry run mypy $(PY_FILES)

fmt: install
	poetry run black $(PY_FILES)


generate:
	poetry run ./hack/tekton-task-embed-script.py task/tekton-slack-task-status.yaml | tee tekton-slack-task-status.yaml
