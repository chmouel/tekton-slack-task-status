all: generate

install:
	poetry install || true

lint: install
	poetry run pylint ./hack/tekton-task-embed-script.py
	poetry run mypy ./hack/tekton-task-embed-script.py

generate:
	poetry run ./hack/tekton-task-embed-script.py task/tekton-slack-task-status.yaml | tee tekton-slack-task-status.yaml
