# -*- coding: utf-8 -*-
"""
本模块负责插件的数据管理，包括文件路径管理和用户数据的加载与保存。
course_schedule/
├── userdata.json # {group_id: [user_id, ...]}
├── ics/
│   ├── user_id.ics
│   └── ...
"""
import json
from pathlib import Path
from typing import Dict, List

import nonebot_plugin_localstore as store


class DataManager:
    """数据管理类"""

    def __init__(self):
        self.data_path: Path = Path(store.get_plugin_config_dir())
        self.ics_path: Path = self.data_path / "ics"
        self.user_data_file: Path = self.data_path / "userdata.json"
        self._init_data()

    def _init_data(self):
        """初始化插件数据文件和目录"""
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.ics_path.mkdir(exist_ok=True)
        if not self.user_data_file.exists():
            with open(self.user_data_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def load_user_data(self) -> Dict[str, List[int]]:
        """加载用户数据"""
        try:
            with open(self.user_data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_user_data(self, user_data: Dict):
        """保存用户数据"""
        with open(self.user_data_file, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)

    def add_user_to_group(self, user_id: int, group_id: int):
        """将用户加入本群列表"""
        user_data = self.load_user_data()
        group_id = str(group_id)
        if group_id not in user_data:
            user_data[group_id] = []
        if user_id not in user_data[group_id]:
            user_data[group_id].append(user_id)
        self.save_user_data(user_data)

    def remove_user_from_group(self, user_id: int, group_id: int):
        """将用户从本群列表中移除"""
        user_data = self.load_user_data()
        group_id = str(group_id)
        user_data[group_id].remove(user_id)
        if not user_data[group_id]:
            del user_data[group_id]
        self.save_user_data(user_data)

    def is_user_bound(self, user_id: int, group_id: int) -> bool:
        """判断该用户是否在本群列表中"""
        user_data = self.load_user_data()
        group_id = str(group_id)

        if (
            not group_id
            or group_id not in user_data
            or user_id not in user_data[group_id]
        ):
            return False
        return True

    def get_ics_file_path(self, user_id: int) -> Path:
        """获取用户的 ICS 文件路径"""
        return self.ics_path / f"{user_id}.ics"


data_manager = DataManager()
