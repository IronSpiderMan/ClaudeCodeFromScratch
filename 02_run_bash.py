#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Author: ZackFair
# @Desc: 
# @File: 02_run_bash.py
# @Date: 2026/4/11 19:43
import json
import subprocess
from typing import List, Dict

from openai import Client

from common.config import WORKDIR, AgentConfig


def run_bash(command: str) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"

    return (result.stdout + result.stderr).strip() or "(no output)"


tools = [{
    "type": "function",
    "function": {
        "name": "run_bash",
        "description": "Run a bash command.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to run."
                }
            },
            "required": ["command"]
        }
    }
}]

tool_handler = {
    'run_bash': run_bash
}


class Agent:

    def __init__(self, config: AgentConfig):
        self.config = config
        self.client = Client(
            base_url=self.config.base_url,
            api_key=self.config.api_key
        )

    def run(self, messages: List[Dict]) -> List[Dict]:
        system_prompt = [{'role': 'system', 'content': self.config.system_prompt}]
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=system_prompt + messages,
            tools=tools,
        )
        if not response.choices[0].finish_reason == 'tool_calls':
            return messages + [response.choices[0].message.model_dump()]

        # 加入工具调用消息
        messages.append(response.choices[0].message.model_dump())

        for tool_call in response.choices[0].message.tool_calls:
            tool_call_id = tool_call.id
            name = tool_call.function.name
            args = tool_call.function.arguments

            print("[Tool Call] >", f"{name}({args})")

            tool = tool_handler.get(name)
            result = tool(**json.loads(args))

            print("[Tool Result] >", result)

            # 加入工具结果消息
            messages.append({'role': 'tool', 'content': result, 'tool_call_id': tool_call_id})

        return self.run(messages)


if __name__ == '__main__':
    agent = Agent(AgentConfig())
    history = []
    while True:
        i = input("Human >")
        if i == 'q':
            break
        history.append({'role': 'user', 'content': i})
        history = agent.run(history)
        print("Assistant >", history[-1].get('content'))
