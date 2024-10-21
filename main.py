import asyncio
from user_manager import UserManager

if __name__ == "__main__":
    async def main():
        # 创建一个用户管理器实例
        user_manager = UserManager()
        
        # 让用户管理器启动并管理所有用户的任务
        await user_manager.start_users()

    # 使用 asyncio.run 来启动事件循环并运行主协程
    asyncio.run(main())