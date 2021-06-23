all: generate

generate: 
	@./hack/tekton-task-embed-script.py task/tekton-slack-task-status.yaml | tee tekton-slack-task-status.yaml
