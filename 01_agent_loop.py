#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Author: ZackFair
# @Desc: 
# @File: 01_agent_loop.py
# @Date: 2026/4/11 19:27
from typing import List, Dict
from dataclasses import dataclass

from openai import Client


@dataclass
class AgentConfig:
    base_url: str = "http://127.0.0.1:11434/v1"
    api_key: str = "<KEY>"
    model: str = "qwen3.5:0.8b"

    system_prompt: str = "你是一个 AI 助手。"


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
        )
        return messages + [response.choices[0].message.model_dump()]


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
