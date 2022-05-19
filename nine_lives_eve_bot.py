import argparse
import logging
import os

import discord
from discord.ext import commands

from cogs.cap_monitor_cog import CapMonitorCog
from cogs.monitor_cog import MonitorCog

CORP_DISCORD_CHANNEL = 918237769447399456

logger = logging.getLogger('nine-lives-eve-bot')
logger.setLevel(logging.INFO)


class NineLivesEveBot(commands.Bot):
    async def on_ready(self):
        logger.info(f'Logged in as {self.user.name}')


def main():
    intents = discord.Intents.default()

    bot = NineLivesEveBot(command_prefix='$', intents=intents)

    # enemy_monitor_cog = MonitorCog(bot, sound=sound, debug_mode=debug_mode, discord_report_channel=CORP_DISCORD_CHANNEL)
    cap_monitor_cog = CapMonitorCog(bot, CORP_DISCORD_CHANNEL)

    bot.add_cog(cap_monitor_cog)
    bot.run(token)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-t', help='Discord token', required=True)
    parser.add_argument('-m', default=False, action='store_true', help='Mute local alarm sound')
    parser.add_argument('-d', default=False, action='store_true', help='Debug mode')

    args = parser.parse_args()

    token = args.t
    sound = not args.m
    debug_mode = args.d

    logger.info(f'Discord authentication token: {token}.')
    logger.info(f'Alarms sound: {sound}.')
    logger.info(f'Debug mode: {debug_mode}.')

    os.makedirs('tmp', exist_ok=True)
    if debug_mode:
        os.makedirs('verify', exist_ok=True)

    main()
