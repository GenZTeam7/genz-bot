# update 1
import discord
from discord.ext import commands
import json
import time
import datetime
import os
import random
from collections import defaultdict, deque

# ตั้งค่า Intent
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== ระบบกันสแปม =====
SPAM_LIMIT = 5
SPAM_TIME = 5
MUTE_TIME = 60
antispam_enabled = defaultdict(lambda: True)
spam_tracker = defaultdict(lambda: deque())

# ===== ระบบเวล (Level) =====
xp_data = defaultdict(int)
level_data = defaultdict(int)
def get_level(xp):
    # ทุก 150 XP = 1 เวล (ปรับได้)
    return int(xp // 150)

# ===== ปุ่มกดรับยศเกม =====
class GameRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Valorant", style=discord.ButtonStyle.red, emoji="🔫")
    async def valorant(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Valorant")
        if not role:
            role = await interaction.guild.create_role(name="Valorant", colour=discord.Colour.red())
        await self.toggle_role(interaction, role)

    @discord.ui.button(label="Roblox", style=discord.ButtonStyle.blurple, emoji="🎮")
    async def roblox(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Roblox")
        if not role:
            role = await interaction.guild.create_role(name="Roblox", colour=discord.Colour.blue())
        await self.toggle_role(interaction, role)

    @discord.ui.button(label="Minecraft", style=discord.ButtonStyle.green, emoji="⛏️")
    async def minecraft(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Minecraft")
        if not role:
            role = await interaction.guild.create_role(name="Minecraft", colour=discord.Colour.green())
        await self.toggle_role(interaction, role)

    async def toggle_role(self, interaction, role):
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"❌ ลบยศ {role.name} แล้ว", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"✅ รับยศ {role.name} แล้ว", ephemeral=True)

@bot.event
async def on_ready():
    print(f"บอทออนไลน์แล้ว: {bot.user}")
    bot.add_view(GameRoleView())  # ให้ปุ่มทำงานหลังรีบอท

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

# ===== ต้อนรับคนเข้าใหม่ =====
@bot.event
async def on_member_join(member):
    channel = member.guild.system_channel
    if not channel:
        # หาห้องแรกที่ส่งได้
        for ch in member.guild.text_channels:
            if ch.permissions_for(member.guild.me).send_messages:
                channel = ch
                break
    if channel:
        embed = discord.Embed(title=f"ยินดีต้อนรับ {member.name} 🎉", description=f"เข้าดิส **{member.guild.name}** แล้ว\nพิมพ์ `!rank` เช็คเวล | `!roles` รับยศเกม", color=0x00ff00)
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return

    # --- ระบบเวล: ให้ XP ทุกข้อความ (แม้แอดมินก็ได้เวล) ---
    if message.guild:
        uid = message.author.id
        xp_data[uid] += random.randint(10, 20)
        new_level = get_level(xp_data[uid])
        if new_level > level_data[uid]:
            level_data[uid] = new_level
            try:
                await message.channel.send(f"🎉 {message.author.mention} เลเวลอัพเป็น **เวล {new_level}** แล้ว! (XP: {xp_data[uid]})")
            except: pass

    # --- แอดมินข้ามกันสแปม ---
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

# ===== คำสั่งเวล =====
@bot.command(name="rank")
async def rank(ctx, member: discord.Member = None):
    target = member or ctx.author
    xp = xp_data[target.id]
    lv = get_level(xp)
    need = (lv+1)*150 - xp
    embed = discord.Embed(title=f"Rank: {target.display_name}", color=0x3498db)
    embed.add_field(name="เลเวล", value=str(lv))
    embed.add_field(name="XP", value=f"{xp} / {(lv+1)*150}")
    embed.add_field(name="อีก", value=f"{need} XP จะอัพเวล", inline=False)
    if target.display_avatar:
        embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="top")
async def top(ctx):
    if not xp_data:
        await ctx.send("ยังไม่มีใครมี XP เลย")
        return
    sorted_xp = sorted(xp_data.items(), key=lambda x: x[1], reverse=True)[:10]
    msg = "**🏆 Top 10 เวลสูงสุด**\n"
    for i, (uid, xp) in enumerate(sorted_xp, 1):
        member = ctx.guild.get_member(uid)
        name = member.display_name if member else f"ID:{uid}"
        msg += f"{i}. {name} — เวล {get_level(xp)} ({xp} XP)\n"
    await ctx.send(msg)

# ===== ปุ่มรับยศ =====
@bot.command(name="roles")
@is_admin()
async def roles(ctx):
    embed = discord.Embed(title="กดรับยศเกม 🎮", description="กดปุ่มด้านล่างเพื่อรับยศเกมที่เล่น\nกดอีกทีเพื่อลบยศออก", color=0x9b59b6)
    await ctx.send(embed=embed, view=GameRoleView())

# ===== มีม + สุ่ม =====
@bot.command(name="meme")
async def meme(ctx):
    memes = [
        "https://i.imgflip.com/65efzo.jpg",
        "https://i.imgflip.com/26am.jpg",
        "https://i.imgflip.com/1bij.jpg",
        "https://i.imgflip.com/1g8my4.jpg",
    ]
    embed = discord.Embed(title="มีม GenZ 😂", color=0xf1c40f)
    embed.set_image(url=random.choice(memes))
    await ctx.send(embed=embed)

@bot.command(name="สุ่ม")
async def random_cmd(ctx, *, choices: str = None):
    if not choices:
        await ctx.send("ใช้: `!สุ่ม พิซซ่า ชาบู หมูกระทะ`")
        return
    # แยกด้วยช่องว่างหรือจุลภาค
    items = [c.strip() for c in choices.replace(",", " ").split() if c.strip()]
    await ctx.send(f"🎲 สุ่มได้: **{random.choice(items)}**")

# ===== คำสั่งเดิม =====
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

# รันบอท
TOKEN = os.getenv("DISCORD_TOKEN") or "ใส่_TOKEN_ใหม่ตรงนี้"
bot.run(TOKEN)
