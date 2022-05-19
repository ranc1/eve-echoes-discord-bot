import asyncio
import logging

import airtest.core.api as airtest
import cv2
import discord
from airtest.core.cv import Template
from discord.ext import tasks, commands

from utils import monitor

SCREENSHOT_DIR = 'tmp'
RESOURCE_DIR = 'resource'

logger = logging.getLogger('cap_monitor_cog')
logger.setLevel(logging.INFO)


class CapMonitorCog(commands.Cog):
    def __init__(self, bot, discord_report_channel):
        self.bot = bot
        self.discord_report_channel = discord_report_channel
        self.run_bot_task.start()
        self.reported = False

    @tasks.loop()
    async def run_bot_task(self):
        screenshot_file_name = f'{SCREENSHOT_DIR}/cap_monitor_screen_overview.png'
        airtest.snapshot(screenshot_file_name)
        screen = cv2.imread(screenshot_file_name, cv2.IMREAD_UNCHANGED)

        no_result = Template(f"{RESOURCE_DIR}/no_search_result.png", threshold=0.75, resolution=(1440, 1080))
        if not no_result.match_in(screen):
            ships = screen[60:750, 1090:1439]
            cv2.imwrite(f'{SCREENSHOT_DIR}/ships.png', ships)

            if not self.reported:
                logger.info('Found ships! Reporting to Discord...')
                channel = self.bot.get_channel(self.discord_report_channel)
                await channel.send('Capital ships!', file=discord.File(f'{monitor.SCREENSHOT_DIR}/ships.png'))
                self.reported = True
        else:
            self.reported = False

        await asyncio.sleep(20)

    @run_bot_task.before_loop
    async def before_run_bot_task(self):
        await self.bot.wait_until_ready()
        monitor.initialize_device()
        logger.info('Device connected. Start monitoring...')