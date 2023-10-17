import discord
from discord.ext import commands
import re

class URLConverter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return  # Ignore messages from bots

        content = message.content
        new_url = None

        if "https://twitter.com/" in content:
            new_url = content.replace("https://twitter.com/", "https://fxtwitter.com/")
        elif "https://x.com/" in content:
            new_url = content.replace("https://x.com/", "https://fxtwitter.com/")

        if new_url:
            await message.reply(new_url)  # reply to the original message with the new URL


async def setup(bot):
    await bot.add_cog(URLConverter(bot))