import discord
import asyncio
import monitor
import winsound
import logging
import os
import time
from shutil import copy2

from discord.ext import tasks, commands

logger = logging.getLogger('eve-monitor-bot')
logger.setLevel(logging.INFO)


class MonitorCog(commands.Cog):
    def __init__(self, bot, sound=True, corp_report=True, debug_mode=False):
        self.bot = bot
        self.corp_report = corp_report
        self.discord_report = True
        self.sound = sound
        self.debug_mode = debug_mode
        self.prev_hostile_count = 0
        self.prev_neutral_count = 0
        self.last_successful_scan = time.time()

        monitor_logger = logging.getLogger('eve-monitor')
        monitor_logger.setLevel(logging.DEBUG) if self.debug_mode else monitor_logger.setLevel(logging.INFO)

        self.run_bot_task.start()

    async def report_discord(self, local_standings):
        channel = self.bot.get_channel(918237769447399456)
        hostile_count = len(local_standings[monitor.HOSTILE])
        neutral_count = len(local_standings[monitor.NEUTRAL])

        if hostile_count + neutral_count == 0:
            await channel.send('Clear')
        else:
            message = f'Hostile: {hostile_count}, Neutral: {neutral_count}'
            await channel.send(message, file=discord.File('tmp/screen_local.png'))

    @commands.command()
    async def ping(self, ctx):
        if self.debug_mode:
            await ctx.send('Currently in Debug Mode...')
        elif time.time() - self.last_successful_scan > 60:
            await ctx.send(f'Service Unavailable! Last scan: {time.ctime(self.last_successful_scan)} PST')
        else:
            await ctx.send('Online')

    @commands.command()
    async def shutdown(self, ctx):
        if self.discord_report:
            await ctx.send("You didn't actually think I will let you shut me down, did you? Anyways, I will leave you alone for now.")
            self.discord_report = False
        else:
            await ctx.send("Dude, I am already down. What more do you want from me?")

    @commands.command()
    async def resume(self, ctx):
        if self.discord_report:
            await ctx.send('?')
        else:
            await ctx.send('Huh... Now you regret.')
            self.discord_report = True

    @tasks.loop()
    async def run_bot_task(self):
        local_details = monitor.identify_local_in_overview()
        if local_details is not None:
            hostile_count = local_details[monitor.HOSTILE]
            neutral_count = local_details[monitor.NEUTRAL]
            friendly_count = local_details[monitor.FRIENDLY]
            total_count = hostile_count + neutral_count + friendly_count

            if hostile_count > 0 or neutral_count > 0:
                if self.sound:
                    winsound.Beep(440, 250)

            if hostile_count != self.prev_hostile_count or neutral_count != self.prev_neutral_count or total_count >= 7:
                local_standings = monitor.identify_local_in_chat()

                chat_hostile_count = len(local_standings[monitor.HOSTILE])
                chat_neutral_count = len(local_standings[monitor.NEUTRAL])
                chat_friendly_count = len(local_standings[monitor.FRIENDLY])
                logger.info(f'Overview | Hostile: {hostile_count}. Neutral: {neutral_count}. Friendly: {friendly_count}.')
                logger.info(f'Chat     | Hostile: {chat_hostile_count}. Neutral: {chat_neutral_count}. Friendly: {chat_friendly_count}.')
                logger.info('=========================================================================')

                if chat_hostile_count != self.prev_hostile_count or chat_neutral_count != self.prev_neutral_count:
                    if self.discord_report:
                        await self.report_discord(local_standings)

                    if self.corp_report:
                        monitor.report(local_standings)
                    else:
                        # After identify_local_in_chat, the chat is still open.
                        monitor.close_chat()
                else:
                    # After identify_local_in_chat, the chat is still open.
                    monitor.close_chat()

                if (hostile_count != chat_hostile_count or neutral_count != chat_neutral_count or friendly_count != chat_friendly_count) and self.debug_mode:
                    path = 'verify/' + str(int(time.time()))
                    os.mkdir(path)
                    copy2('tmp/screen_overview.png', path + '/' + str(hostile_count) + '-' + str(neutral_count) + '-' + str(friendly_count) + '-overview.png')
                    copy2('tmp/screen_chat.png', path + '/' + str(chat_hostile_count) + '-' + str(chat_neutral_count) + '-' + str(chat_friendly_count) + '-chat.png')

                self.prev_hostile_count = chat_hostile_count
                self.prev_neutral_count = chat_neutral_count

            self.last_successful_scan = time.time()

        if self.prev_hostile_count + self.prev_neutral_count == 0:
            await asyncio.sleep(10)  # local safe. additional sleep to save CPU.
        else:
            await asyncio.sleep(5)

    @run_bot_task.before_loop
    async def before_run_bot_task(self):
        await self.bot.wait_until_ready()
        monitor.initialize_device()
        logger.info('Device connected. Start monitoring...')
