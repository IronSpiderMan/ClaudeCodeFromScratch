#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Author: ZackFair
# @Desc: 
# @File: 04_todo.py
# @Date: 2026/4/11 20:19
import json
import subprocess
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional

from openai import Client

from common.config import WORKDIR, AgentConfig

from pydantic import BaseModel


class PlanItemStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class PlanItem(BaseModel):
    content: str
    status: PlanItemStatus = 'pending'
    parent: Optional[str] = None


class TodoManager:

    def __init__(self, max_items: int = 12):
        self.items: List[PlanItem] = []
        self.max_items = max_items

    def update(self, items: List[PlanItem]) -> str:
        if len(items) > self.max_items:
            raise ValueError(f"Keep the session plan short than {self.max_items} items.")

        if sum([item.status == PlanItemStatus.in_progress for item in items]) > 1:
            raise ValueError(f"Only one item can be in progress.")

        self.items = items
        return self.render()

    def render(self):
        lines = []
        for item in self.items:
            marker = {
                "pending": "[ ]",
                "in_progress": "[>]",
                "completed": "[x]",
            }[item.status]
            line = f"{marker} {item.content}"
            if item.status == "in_progress" and item.parent:
                line += f" ({item.parent})"
            lines.append(line)
        completed = sum(1 for item in self.items if item.status == "completed")
        lines.append(f"\n({completed}/{len(self.items)} completed)")
        return "\n".join(lines)


todo_manager = TodoManager()


def todo(items: List[PlanItem]) -> str:
    if isinstance(items, str):
        items = json.loads(items)
    for idx, item in enumerate(items):
        if isinstance(item, dict):
            items[idx] = PlanItem(**item)
    return todo_manager.update(items)


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
    },
    {
        "type": "function",
        "function": {
            "name": "todo",
            "description": "Update the agent's task plan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "Ordered list of plan items.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "Content of the plan."
                                },
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "completed"],
                                    "description": "Status of the plan."
                                },
                                "parent": {
                                    "type": "string",
                                    "description": "Parent of the plan."
                                }
                            }
                        }
                    },
                },
                "required": ["items"]
            }
        }
    },
]

tool_handler = {
    'run_bash': run_bash,
    'read_file': read_file,
    'edit_file': edit_file,
    'write_file': write_file,
    'todo': todo
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
    agent = Agent(
        AgentConfig(
            system_prompt="""Must use the todo tool for multi-step work.
    Keep exactly one step in_progress when a task has multiple steps.
    Refresh the plan as work advances. Prefer tools over prose."""
        )
    )

    history = []
    while True:
        i = input("Human >")
        if i == 'q':
            break
        history.append({'role': 'user', 'content': i})
        history = agent.run(history)
        print("Assistant >", history[-1].get('content'))
