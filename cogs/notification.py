import discord
from discord import app_commands
from core.classes import Cog_Extension
from tweety import Twitter
from datetime import datetime, timezone
from dotenv import load_dotenv
import os
import sqlite3

from src.log import setup_logger
from src.notification.account_tracker import AccountTracker
from src.permission_check import is_administrator

log = setup_logger(__name__)

load_dotenv()

class Notification(Cog_Extension):
    def __init__(self, bot):
        super().__init__(bot)
        self.account_tracker = AccountTracker(bot)

    add_group = app_commands.Group(name='add', description="Add something")


    @is_administrator()
    @add_group.command(name='notifier')
    async def notifier(self, itn : discord.Interaction, username: str, channel: discord.TextChannel, mention: discord.Role = None):
        """特定のチャンネルでTwitterユーザーを追加します。

        Parameters
        -----------
        username: str
            通知をオンにしたいTwitterユーザーのユーザーネーム。
        channel: discord.TextChannel
            ボットが通知を投稿するチャンネル。
        mention: discord.Role
            通知時に言及するロール。
        """
        
        await itn.response.defer(ephemeral=True)
        
        conn = sqlite3.connect(f"{os.getenv('DATA_PATH')}tracked_accounts.db")
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT * FROM user WHERE username='{username}'")
        match_user = cursor.fetchone()
        
        roleID = str(mention.id) if mention != None else ''
        if match_user == None:
            app = Twitter("session")
            app.load_auth_token(os.getenv('TWITTER_TOKEN'))
            try:
                new_user = app.get_user_info(username)
            except:
                await itn.followup.send(f'{username}が見つかりませんでした', ephemeral=True)
                return
            
            cursor.execute('INSERT INTO user VALUES (?, ?, ?)', (str(new_user.id), username, datetime.utcnow().replace(tzinfo=timezone.utc).strftime('%Y-%m-%d %H:%M:%S%z')))
            cursor.execute('INSERT OR IGNORE INTO channel VALUES (?)', (str(channel.id),))
            cursor.execute('INSERT INTO notification VALUES (?, ?, ?)', (str(new_user.id), str(channel.id), roleID))
            
            app.follow_user(new_user)
            
            if app.enable_user_notification(new_user): log.info(f'{username}の通知をオンにしました!')
            else: log.warning(f'{username}の通知をオンにできませんでした')
        else:
            cursor.execute('INSERT OR IGNORE INTO channel VALUES (?)', (str(channel.id),))
            cursor.execute('REPLACE INTO notification VALUES (?, ?, ?)', (match_user[0], str(channel.id), roleID))
        
        conn.commit()
        conn.close()
            
        if match_user == None: await self.account_tracker.addTask(username)
            
        await itn.followup.send(f'{username}の通知を{channel}に登録しました!', ephemeral=True)
    
    @is_administrator()
    @app_commands.command(name='remove_notifier')
    async def remove_notifier(self, itn: discord.Interaction, username: str):
        """通知リストからTwitterユーザーを削除します。

        Parameters
        -----------
        username: str
            通知をオフにしたいTwitterユーザーのユーザーネーム。
        """
        
        await itn.response.defer(ephemeral=True)
        
        conn = sqlite3.connect(f"{os.getenv('DATA_PATH')}tracked_accounts.db")
        cursor = conn.cursor()
        
        # Check if the user exists in the database
        cursor.execute(f"SELECT * FROM user WHERE username='{username}'")
        match_user = cursor.fetchone()
        
        if match_user is None:
            await itn.followup.send(f'{username}の通知は、登録または追加されていません。', ephemeral=True)
            return
        
        # Remove entries from the database
        cursor.execute(f"DELETE FROM user WHERE username='{username}'")
        cursor.execute(f"DELETE FROM notification WHERE user_id='{match_user[0]}'")
        
        conn.commit()
        conn.close()

        # Optionally, use the Twitter API to turn off notifications
        # (assuming the `tweety` module and `Twitter` class have the necessary methods)
        app = Twitter("session")
        app.load_auth_token(os.getenv('TWITTER_TOKEN'))
        user_info = app.get_user_info(username)
        app.unfollow_user(user_info)
        app.disable_user_notification(user_info)

        await itn.followup.send(f'{username}の通知を正常に削除しました！', ephemeral=True)


async def setup(bot):
	await bot.add_cog(Notification(bot))