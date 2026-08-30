import discord
from discord.ext import commands
import json
import time
import datetime
import os
from collections import defaultdict, deque

# ตั้งค่า Intent
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== ระบบกันสแปม =====
SPAM_LIMIT = 5  # พิมพ์เกิน 5 ข้อความ
SPAM_TIME = 5   # ภายใน 5 วินาที = ถือว่าสแปม
MUTE_TIME = 60  # โดน timeout 60 วินาที
antispam_enabled = defaultdict(lambda: True)
spam_tracker = defaultdict(lambda: deque())
# ======================

@bot.event
async def on_ready():
    print(f"บอทออนไลน์แล้ว: {bot.user}")

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return
    if message.guild and message.author.guild_permissions.administrator:
        await bot.process_commands(message)
        return
    if message.guild and not antispam_enabled[message.guild.id]:
        await bot.process_commands(message)
        return

    if message.guild:
        user_id = message.author.id
        now = time.time()
        dq = spam_tracker[user_id]
        dq.append(now)
        while dq and now - dq[0] > SPAM_TIME:
            dq.popleft()

        if len(dq) > SPAM_LIMIT:
            try:
                try: await message.delete()
                except: pass
                try:
                    def is_spammer(m): return m.author.id == user_id
                    await message.channel.purge(limit=20, check=is_spammer, bulk=True)
                except: pass
                try:
                    # แก้บัคตรงนี้: ใช้ datetime.timedelta ไม่ใช่ discord.timedelta
                    until = discord.utils.utcnow() + datetime.timedelta(seconds=MUTE_TIME)
                    await message.author.timeout(until, reason="สแปมข้อความถี่เกินไป (Anti-Spam)")
                    await message.channel.send(f"⚠️ {message.author.mention} สแปมเกิน {SPAM_LIMIT} ข้อความ/{SPAM_TIME}วิ → ลบข้อความทั้งหมด + mute {MUTE_TIME} วินาที", delete_after=10)
                except Exception as e:
                    print(f"Timeout failed: {e}")
                    await message.channel.send(f"⚠️ {message.author.mention} อย่าสแปมครับ! ข้อความถูกลบแล้ว แต่ mute ไม่สำเร็จ (เช็คสิทธิ์ Moderate Members และยศบอท)", delete_after=10)
                dq.clear()
                return
            except:
                pass

        if "discord.gg/" in message.content or "discord.com/invite/" in message.content:
            try:
                try: await message.delete()
                except: pass
                try:
                    until = discord.utils.utcnow() + datetime.timedelta(seconds=MUTE_TIME)
                    await message.author.timeout(until, reason="ส่งลิงก์เชิญดิสคอร์ด (Anti-Spam)")
                    await message.channel.send(f"⚠️ {message.author.mention} ห้ามส่งลิงก์ดิสครับ → mute {MUTE_TIME} วิ", delete_after=10)
                except:
                    await message.channel.send(f"⚠️ {message.author.mention} ห้ามส่งลิงก์เชิญดิสคอร์ดครับ (ลบแล้ว)", delete_after=5)
                return
            except:
                pass

    await bot.process_commands(message)

@bot.command(name="antispam")
@is_admin()
async def antispam(ctx, mode: str = None):
    if mode == "on":
        antispam_enabled[ctx.guild.id] = True
        await ctx.send("✅ เปิดระบบกันสแปมแล้ว (5 ข้อความ/5วิ = mute 60วิ + กันลิงก์ discord.gg)")
    elif mode == "off":
        antispam_enabled[ctx.guild.id] = False
        await ctx.send("❌ ปิดระบบกันสแปมแล้ว")
    else:
        status = "เปิด ✅" if antispam_enabled[ctx.guild.id] else "ปิด ❌"
        await ctx.send(f"สถานะกันสแปมตอนนี้: {status}\nใช้ `!antispam on` หรือ `!antispam off`")

@bot.command(name="setspam")
@is_admin()
async def setspam(ctx, limit: int = None, seconds: int = None, mute: int = None):
    global SPAM_LIMIT, SPAM_TIME, MUTE_TIME
    if limit is None:
        await ctx.send(f"ตั้งค่าปัจจุบัน: `{SPAM_LIMIT} ข้อความ / {SPAM_TIME} วินาที = mute {MUTE_TIME} วิ`\nใช้: `!setspam จำนวนข้อความ วินาที เวลาmute` เช่น `!setspam 5 5 120`")
        return
    SPAM_LIMIT = limit
    if seconds: SPAM_TIME = seconds
    if mute: MUTE_TIME = mute
    await ctx.send(f"✅ ตั้งค่าใหม่แล้ว: `{SPAM_LIMIT} ข้อความ / {SPAM_TIME} วิ = mute {MUTE_TIME} วิ` + ลบข้อความย้อนหลังทั้งหมด")

@bot.command(name="clear")
@is_admin()
async def clear(ctx, amount: int = 10):
    if amount > 100:
        await ctx.send("ลบได้ครั้งละไม่เกิน 100 ข้อความครับ")
        return
    deleted = await ctx.channel.purge(limit=amount+1)
    await ctx.send(f"ลบไป {len(deleted)-1} ข้อความแล้ว ✅", delete_after=5)

@bot.command(name="create-channel")
@is_admin()
async def create_channel(ctx, *, name: str):
    await ctx.guild.create_text_channel(name)
    await ctx.send(f"สร้างห้อง `{name}` สำเร็จ ✅")

@bot.command(name="delete-channel")
@is_admin()
async def delete_channel(ctx, channel: discord.TextChannel):
    await ctx.send(f"คุณต้องการลบห้อง {channel.mention} จริงๆใช่มั้ย? พิมพ์ `ยืนยัน` ภายใน 15 วินาที")
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content == "ยืนยัน"
    try:
        await bot.wait_for('message', check=check, timeout=15.0)
        await channel.delete(reason=f"ลบโดย {ctx.author}")
        await ctx.send(f"ลบห้อง {channel.name} แล้ว ✅")
    except:
        await ctx.send("ยกเลิกการลบ ❌ (หมดเวลา/ไม่ได้พิมพ์ยืนยัน)")

@bot.command(name="backup")
@is_admin()
async def backup(ctx):
    data = {
        "guild": ctx.guild.name,
        "channels": [c.name for c in ctx.guild.channels],
        "roles": [r.name for r in ctx.guild.roles]
    }
    with open(f"backup_{ctx.guild.id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    await ctx.send("Backup เสร็จแล้ว ✅ ได้ไฟล์ `backup_...json`", file=discord.File(f"backup_{ctx.guild.id}.json"))

# รันบอท - ใส่ Token ที่นี่ (ไป Reset Token ก่อน แล้วเอาอันใหม่มาใส่)
TOKEN = os.getenv("Token_YOU") or "Token_YOU"
bot.run(TOKEN)
