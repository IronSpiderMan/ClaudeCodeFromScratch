#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Author: ZackFair
# @Desc: 
# @File: 03_file_operation.py
# @Date: 2026/4/11 20:08
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

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


def read_file(path: str, limit: Optional[int] = None) -> str:
    try:
        lines = Path(path).read_text().splitlines()
        if limit and limit <= len(lines):
            lines = lines[: limit] + [f"...({len(lines) - limit} more liens)"]
        output = "\n".join(lines)
        return output
    except Exception as e:
        return f"Error: {e}"


def edit_file(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = Path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
    except Exception as e:
        return f"Error: {e}"


def write_file(path: str, text: str) -> str:
    try:
        fp = Path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(text)
        return f"Wrote {len(text)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


tools = [
    {
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
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of lines to read."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file (overwrite if exists)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path"
                    },
                    "text": {
                        "type": "string",
                        "description": "Content to write"
                    }
                },
                "required": ["path", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file by replacing old text with new text (only first occurrence)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path"
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Text to replace"
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text"
                    }
                },
                "required": ["path", "old_text", "new_text"]
            }
        }
    }
]

tool_handler = {
    'run_bash': run_bash,
    'read_file': read_file,
    'edit_file': edit_file,
    'write_file': write_file
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
