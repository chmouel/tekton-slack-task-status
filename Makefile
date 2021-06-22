all: generate

generate: 
	@./hack/tekton-task-embed-script.py task/tekton-slack-task-status.py | tee tekton-slack-task-status.yaml
