import discord
from discord.ext import commands
import logging
from monitor_cog import MonitorCog

logger = logging.getLogger('nine-lives-eve-bot')
logger.setLevel(logging.INFO)


class NineLivesEveBot(commands.Bot):
    async def on_ready(self):
        logger.info(f'Logged in as {self.user.name}')


def main():
    token = ''

    intents = discord.Intents.default()

    bot = NineLivesEveBot(command_prefix='$', intents=intents)

    bot.add_cog(MonitorCog(bot))
    bot.run(token)


if __name__ == '__main__':
    main()

