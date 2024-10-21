import yuketang
import asyncio
import json
import os
from yuketang import ykt_user

current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
with open('config.json', 'r', encoding='utf-8') as f:
    user_data = json.load(f)

class UserManager:
    def __init__(self):
        self.users = {}  # 存储用户的会话
        self.load_users()

    def load_users(self):
        for user_info in user_data['users']:
            # 为每个用户创建 Yuketang 实例
            name = user_info['name']
            openId = user_info['openId']
            self.users[name] = yuketang.yuketang(name, openId)
            
    async def start_users(self):
        """为每个用户启动 ykt_user 异步任务"""
        tasks = []
        for name in self.users:
            # 从 self.users 字典中获取每个用户的 Yuketang 实例
            ykt_instance = self.users[name]
            # 为每个用户创建一个异步任务，调用 ykt_user 函数
            tasks.append(asyncio.create_task(ykt_user(ykt_instance)))
        
        # 并行执行所有任务
        await asyncio.gather(*tasks)



