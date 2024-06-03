
import discord
import requests
import json

from discord.ext import commands, tasks
from discord.ext.commands import Context
import time
from dotenv import load_dotenv
import os

load_dotenv()

from helpers import checks

mp_ACCESS_TOKEN = "APP_USR-8596591430506334-012412-5e4f2cce3e1156252a5637ea8120d0f8-764335578"

# # Here we name the cog and create a new class for the cog.
class API(commands.Cog, name="api"):
    def __init__(self, bot):
        self.bot = bot
        self.update_status.start()

    @commands.hybrid_command(
    name="generate-qrcode"
    description="Generate a QR code from mp api"
    )

    async def generate_qrcode(self, ctx: Context, data: str):
        url = "https://api.mercadopago.com/pos"
        headers = {
            "Authorization": f"Bearer {mp_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }



async def setup(bot):
    await bot.add_cog(API(bot))
    