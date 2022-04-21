import discord
import asyncio
from utils import monitor
from utils import beep_player
import logging
import os
import time
from shutil import copy2

from discord.ext import tasks, commands

logger = logging.getLogger('eve-monitor-bot')
logger.setLevel(logging.INFO)


def sound_alarm(count):
    frequency = 440
    duration_in_millis = 250
    for i in range(count):
        beep_player.play(frequency, duration_in_millis / 1000)


class MonitorCog(commands.Cog):
    def __init__(self, bot, sound=True, debug_mode=False, discord_report_channel=None):
        self.bot = bot
        self.sound = sound
        self.debug_mode = debug_mode
        self.prev_hostile_count = 0
        self.prev_neutral_count = 0
        self.last_successful_scan = time.time()
        if discord_report_channel:
            self.discord_report_channel = discord_report_channel
            self.discord_report = True
        else:
            self.discord_report = False

        monitor_logger = logging.getLogger('eve-monitor')
        monitor_logger.setLevel(logging.DEBUG) if self.debug_mode else monitor_logger.setLevel(logging.INFO)

        self.run_bot_task.start()

    async def report_discord(self, local_standings):
        channel = self.bot.get_channel(self.discord_report_channel)
        hostile_count = len(local_standings[monitor.HOSTILE])
        neutral_count = len(local_standings[monitor.NEUTRAL])

        if hostile_count + neutral_count == 0:
            await channel.send('Clear')
        else:
            message = f'Hostile: {hostile_count}, Neutral: {neutral_count}'
            await channel.send(message, file=discord.File(f'{monitor.SCREENSHOT_DIR}/screen_local.png'))

    @commands.command(help='Monitor module health and status report.')
    async def ping(self, ctx):
        if self.debug_mode:
            await ctx.send('Currently in Debug Mode...')
        elif self.__scan_unhealthy():
            await ctx.send(f'Service Unavailable! Last scan: {time.ctime(self.last_successful_scan)} PST')
        else:
            discord_report_status = 'Enabled' if self.discord_report else 'Disabled'
            await ctx.send(f'Online. Discord report: {discord_report_status}')

    @commands.command(help='Shutdown Monitor module.')
    async def shutdown(self, ctx):
        if self.discord_report:
            await ctx.send("You didn't actually think I will let you shut me down, did you? Anyways, I will leave you alone for now.")
            self.discord_report = False
        else:
            await ctx.send("Dude, I am already down. What more do you want from me?")

    @commands.command(help='Resume Monitor module.')
    async def resume(self, ctx):
        if self.discord_report:
            await ctx.send('?')
        else:
            await ctx.send('Huh... Now you regret.')
            self.discord_report = True

    @tasks.loop()
    async def run_bot_task(self):
        try:
            if self.__scan_unhealthy():
                sound_alarm(3)

            await self.__deferred_monitor_task()

            # local safe. additional sleep to save CPU.
            sleep_time = 10 if self.prev_hostile_count + self.prev_neutral_count == 0 else 5
            await asyncio.sleep(sleep_time)
        except Exception as e:
            logger.warning('Monitor task failed!', e)

    @run_bot_task.before_loop
    async def before_run_bot_task(self):
        await self.bot.wait_until_ready()
        monitor.initialize_device()
        logger.info('Device connected. Start monitoring...')

    def __scan_unhealthy(self):
        return time.time() - self.last_successful_scan > 60

    async def __deferred_monitor_task(self):
        local_details = monitor.identify_local_in_overview()
        if local_details is not None:
            hostile_count = local_details[monitor.HOSTILE]
            neutral_count = local_details[monitor.NEUTRAL]
            friendly_count = local_details[monitor.FRIENDLY]
            total_count = hostile_count + neutral_count + friendly_count

            sound_times = min(hostile_count + neutral_count, 3)
            if self.sound and sound_times > 0:
                sound_alarm(sound_times)

            if hostile_count != self.prev_hostile_count or neutral_count != self.prev_neutral_count or total_count >= 7:
                local_standings = monitor.identify_local_in_chat()

                chat_hostile_count = len(local_standings[monitor.HOSTILE])
                chat_neutral_count = len(local_standings[monitor.NEUTRAL])
                chat_friendly_count = len(local_standings[monitor.FRIENDLY])
                logger.info(f'Overview | Hostile: {hostile_count}. Neutral: {neutral_count}. Friendly: {friendly_count}.')
                logger.info(f'Chat     | Hostile: {chat_hostile_count}. Neutral: {chat_neutral_count}. Friendly: {chat_friendly_count}.')
                logger.info('=========================================================================')

                if chat_hostile_count != self.prev_hostile_count or chat_neutral_count != self.prev_neutral_count:
                    if not self.debug_mode:
                        # Only report if not in debug mode.
                        monitor.report(local_standings)

                        if self.discord_report:
                            await self.report_discord(local_standings)

                # After identify_local_in_chat and/or report, the chat is still open.
                monitor.close_chat()

                if (hostile_count != chat_hostile_count or neutral_count != chat_neutral_count or friendly_count != chat_friendly_count) and self.debug_mode:
                    path = f'verify/{str(int(time.time()))}'
                    os.mkdir(path)
                    copy2(f'{monitor.SCREENSHOT_DIR}/screen_overview.png', f'{path}/{str(hostile_count)}-{str(neutral_count)}-{str(friendly_count)}-overview.png')
                    copy2(f'{monitor.SCREENSHOT_DIR}/screen_chat.png', f'{path}/{str(chat_hostile_count)}-{str(chat_neutral_count)}-{str(chat_friendly_count)}-chat.png')

                self.prev_hostile_count = chat_hostile_count
                self.prev_neutral_count = chat_neutral_count

            self.last_successful_scan = time.time()
