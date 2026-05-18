#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Author: ZackFair
# @Desc: 
# @File: config.py
# @Date: 2026/4/11 19:45
from pathlib import Path
from dataclasses import dataclass

WORKDIR = Path().cwd()


@dataclass
class AgentConfig:
    model: str = 'xxx'
    base_url: str = 'http://127.0.0.1:11434/v1'
    api_key: str = 'xx'

    system_prompt: str = "你是一个 AI 助手"
