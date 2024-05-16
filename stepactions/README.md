# Slack Notification StepAction

This is a stepaction to use with the new <https://tekton.dev/docs/pipelines/stepactions/> feature

This used to send a message to a slack channel with the link to the openshift console URL

This can be easily modified to another console or dashboard with stable url scheme.

## Usage

* Create a secret called `slack-webhook-url` with a key `hook_url` with the webhook URL you have generated for the channel you want to send the message to.
* In your PipelineRun at the end you can use this finally step:

```yaml
    finally:
      - name: finally
        params:
          - name: openshift_console_host
            value: "mydomain.openshift.console.route.url"
          - name: namespace
          - name: pipelineRun
        when:
          - input: $(tasks.status)
            operator: in
            values: ["Failed"]
        taskSpec:
          params:
            - name: openshift_console_host
            - name: image_url
          steps:
            - name: send-slack-notification
              ref:
                resolver: http
                params:
                  - name: url
                    value: https://raw.githubusercontent.com/chmouel/tekton-slack-task-status/main/stepactions/stepaction.yaml
              params:
                - name: openshift_console_host
                  value: $(params.openshift_console_host)
                - name: image_url
                  value: $(params.image_url)
                - name: namespace
                  value: "$(context.pipelineRun.namespace)"
                - name: pipelineRun
                  value: "$(context.pipelineRun.name)"

```

This only report on Failure but you can change the `when` operator to `in` to
report on success as well (altho the message may need to be modified in the
stepactions), happy to get pull request to make all of this a bit more configurable.
