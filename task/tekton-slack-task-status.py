#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Chmouel Boudjnah <chmouel@chmouel.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Script to send a slack notification to be plugged in a finally task"""
import argparse
import json
import os
import subprocess
import sys
import typing
import urllib.request


class SlackNotificationError(Exception):
    """Custom exception when we fail"""


def get_openshift_console_url(namespace: str) -> str:
    """Get the openshift console url for a namespace"""
    cmd = (
        "kubectl get route -n openshift-console console -o jsonpath='{.spec.host}'",
    )
    ret = subprocess.run(cmd, shell=True, check=True, capture_output=True)
    if ret.returncode != 0:
        raise SlackNotificationError(
            "Could not detect the location of openshift console url: {ret.stdout.decode()}"
        )
    return f"https://{ret.stdout.decode()}/k8s/ns/{namespace}/tekton.dev~v1beta1~PipelineRun/"


def check_label(label_eval: str, label_to_check: str) -> bool:
    """Check a label: if you get a string that has all the labels as specified
    by github, it will eval it and check if one contains the label_to_check"""
    return bool([x for x in eval(label_eval) if x['name'] == label_to_check])  # pylint: disable=eval-used


def get_json_of_pipelinerun(pipelinerun: str) -> typing.Dict[str, typing.Dict]:
    """Find which namespace where we are running currently by checking the
    pipelinerun namespace"""
    cmd = f"kubectl get pipelinerun {pipelinerun} -o json"
    ret = subprocess.run(cmd, shell=True, check=True, capture_output=True)
    if ret.returncode != 0:
        raise SlackNotificationError(f"Could not run command: {cmd}")
    return json.loads(ret.stdout)


def check_status_of_pipelinerun(
    log_prefix: str,
    jeez: typing.Dict[str,
                      typing.Dict]) -> (typing.List[str], typing.List[str]):
    """Check status of a pipelinerun using kubectl, we avoid the the Running
    ones since we run in finally, it will have a running ones"""
    task_runs = jeez['status']['taskRuns']
    failure = []
    success = []

    pname = jeez['metadata']['name']
    for task in task_runs.keys():
        bname = task.replace(pname + "-", '')
        bname = bname.replace("-" + bname.split("-")[-1], '')
        if log_prefix != "":
            bname = f"<{log_prefix}/{bname}|{bname}>"
        if bool([
                x['message'] for x in task_runs[task]['status']['conditions']
                if x['status'] != 'Running' and x['status'] == 'False'
        ]):
            failure.append(bname)
        else:
            success.append(bname)

    return failure, success


def send_slack_message(webhook_url: str, subject: str, text: str,
                       icon: str) -> str:
    """Send a slack message"""
    msg = {
        "text":
        subject,
        "attachments": [{
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": text,
                    },
                    "accessory": {
                        "type": "image",
                        "image_url": icon,
                        "alt_text": "From tekton with love"
                    }
                },
            ]
        }]
    }

    req = urllib.request.Request(webhook_url,
                                 data=json.dumps(msg).encode(),
                                 headers={"Content-type": "application/json"},
                                 method="POST")
    # TODO: Handle error?
    return urllib.request.urlopen(req).read().decode()


def main() -> int:
    """Main"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--label-to-check", help="Label to check")
    parser.add_argument(
        "--failure-url-image",
        default=os.environ.get(
            "FAILURE_URL_IMAGE",
            "https://publicdomainvectors.org/photos/21826-REMIX-ARRET.png"),
        help="The icon of failure")

    parser.add_argument(
        "--success-url-image",
        default=os.environ.get(
            "SUCCESS_URL_IMAGE",
            "https://publicdomainvectors.org/photos/Checkmark.png"),
        help="The icon of success")

    parser.add_argument("--failure-text",
                        help="The text of the slack message when failure",
                        default=os.environ.get("FAILURE_TEXT",
                                               "CI has failed :cry:"))

    parser.add_argument(
        "--success-text",
        default=os.environ.get("SUCCESS_TEXT", "CI has succeeded :thumbsup:"),
        help="The text of the slack message when succes",
    )

    parser.add_argument("--log-url",
                        default=os.environ.get("LOG_URL"),
                        help="Link to the log url")

    parser.add_argument(
        "--openshift",
        default=os.environ.get("OPENSHIFT"),
        help=
        "Wethere we are running on OpenShift and then auto construct the URL, set this to true"
    )

    parser.add_argument(
        "--github-pull-label",
        default=os.environ.get("GITHUB_PULL_LABEL"),
        help="pull_request.labels dict as get from tekton asa code")

    parser.add_argument("--report-success",
                        default=os.environ.get("REPORT_SUCCESS"),
                        help="wether to report success as well")

    parser.add_argument("--pipelinerun",
                        default=os.environ.get("PIPELINERUN"),
                        help="The pipelinerun to check the status on")

    parser.add_argument("--slack-webhook-url",
                        default=os.environ.get("SLACK_WEBHOOK_URL"),
                        help="Slack webhook URL")

    args = parser.parse_args()
    if args.label_to_check and args.github_pull_label:
        if not check_label(args.github_pull_label, args.label_to_check):
            print(
                f"Pull request doesn't have the label {args.label_to_check} skipping."
            )
            return 0

    if not args.pipelinerun:
        print(
            "error --pipelinerun need to be set via env env variable or other means."
        )
        return 1

    if not args.slack_webhook_url:
        print(
            "error --slack-webhook-url need to be set via env variable or other means."
        )
        return 1

    jeez = get_json_of_pipelinerun(args.pipelinerun)
    namespace = jeez['metadata']['namespace']
    if args.log_url == "" and args.openshift.lower() == "true":
        # TODO: Add tekton dashboard if we can find this automatically
        try:
            args.log_url = get_openshift_console_url(namespace) + \
                args.pipelinerun + "/logs"
        except subprocess.CalledProcessError:
            args.log_url = ""
    elif args.openshift.lower() == "true" and args.log_url != "":
        args.log_url = f"{args.log_url}/k8s/ns/{namespace}/tekton.dev~v1beta1~PipelineRun/{args.pipelinerun}/logs"

    failures, success = check_status_of_pipelinerun(args.log_url, jeez)
    if failures:
        slack_image = args.failure_url_image
        slack_subject = args.failure_text
        slack_text = f"""
        • *Failed Tasks*: {", ".join(failures)}\n• *Successful Tasks*: {", ".join(success)}\n"""
    else:
        slack_image = args.success_url_image
        slack_subject = args.success_text
        slack_text = f"""
        • *Successful Tasks*: {", ".join(success)}\n"""

    if args.log_url:
        slack_text += f"• *PipelineRun logs*: {args.log_url}"

    if not failures and args.report_success.lower() != "true":
        return 0

    ret = send_slack_message(args.slack_webhook_url, slack_subject, slack_text,
                             slack_image)
    if ret:
        print(ret)

    return 0


if __name__ == '__main__':
    sys.exit(main())
