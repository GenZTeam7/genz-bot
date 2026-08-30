import discord
from discord.ext import commands
import json
import time
import datetime
import os
import random
import asyncio
from collections import defaultdict, deque

# ตั้งค่า Intent
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None, case_insensitive=True)

# ===== ระบบกันสแปม =====
SPAM_LIMIT = 5
SPAM_TIME = 5
MUTE_TIME = 60
antispam_enabled = defaultdict(lambda: True)
spam_tracker = defaultdict(lambda: deque())

# ===== ระบบเวล (Level) - มีเซฟไฟล์ให้ไม่หายเมื่อรีบอท =====
xp_data = defaultdict(int)
level_data = defaultdict(int)
XP_FILE = "xp_data.json"

def load_xp():
    try:
        if os.path.exists(XP_FILE):
            with open(XP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.get("xp", {}).items():
                    xp_data[int(k)] = v
                for k, v in data.get("level", {}).items():
                    level_data[int(k)] = v
            print(f"โหลด XP {len(xp_data)} คน")
    except Exception as e:
        print(f"Load XP error: {e}")

def save_xp():
    try:
        with open(XP_FILE, "w", encoding="utf-8") as f:
            json.dump({"xp": dict(xp_data), "level": dict(level_data)}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Save XP error: {e}")

def get_level(xp):
    return int(xp // 150)

load_xp()

# ===== ปุ่มกดรับยศเกม =====
class GameRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Valorant", style=discord.ButtonStyle.red, emoji="🔫", custom_id="role_valorant")
    async def valorant(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_role(interaction, "Valorant", discord.Colour.red())
    @discord.ui.button(label="Roblox", style=discord.ButtonStyle.blurple, emoji="🎮", custom_id="role_roblox")
    async def roblox(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_role(interaction, "Roblox", discord.Colour.blue())
    @discord.ui.button(label="Minecraft", style=discord.ButtonStyle.green, emoji="⛏️", custom_id="role_minecraft")
    async def minecraft(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_role(interaction, "Minecraft", discord.Colour.green())
    async def toggle_role(self, interaction, name, colour):
        try:
            role = discord.utils.get(interaction.guild.roles, name=name)
            if not role:
                role = await interaction.guild.create_role(name=name, colour=colour, reason="Role via button")
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role, reason="Remove via button")
                await interaction.response.send_message(f"❌ ลบยศ {role.name} แล้ว", ephemeral=True)
            else:
                await interaction.user.add_roles(role, reason="Add via button")
                await interaction.response.send_message(f"✅ รับยศ {role.name} แล้ว", ephemeral=True)
        except Exception as e:
            print(f"Role error: {e}")
            try: await interaction.response.send_message(f"❌ ทำไม่ได้: {e}", ephemeral=True)
            except: pass

@bot.event
async def on_ready():
    print(f"บอทออนไลน์แล้ว: {bot.user} | กิลด์ {len(bot.guilds)}")
    try:
        bot.add_view(GameRoleView())
    except: pass

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

# ===== Error Handler รวม ให้บอทไม่ดับ =====
@bot.event
async def on_command_error(ctx, error):
    try:
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้ (ต้องเป็นแอดมิน)")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ พารามิเตอร์ไม่ครบ: {error}")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ ช้าๆหน่อย รอ {error.retry_after:.1f} วิ")
        else:
            print(f"Command error {ctx.command}: {error}")
            await ctx.send(f"❌ เกิดข้อผิดพลาด: {error}", delete_after=10)
    except: pass

GOODBYE_CHANNEL_NAME = "goodbye"
LOG_CHANNEL_NAME = "log"

def get_goodbye_channel(guild):
    for ch in guild.text_channels:
        if "goodbye" in ch.name.lower():
            if ch.permissions_for(guild.me).send_messages:
                return ch
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        return guild.system_channel
    for ch in guild.text_channels:
        if ch.permissions_for(guild.me).send_messages:
            return ch
    return None

def get_log_channel(guild):
    for ch in guild.text_channels:
        if "log" in ch.name.lower():
            if ch.permissions_for(guild.me).send_messages:
                return ch
    return None

# ===== ต้อนรับคนเข้า-ออก (เสถียร) =====
@bot.event
async def on_member_join(member):
    try:
        await asyncio.sleep(1)
        channel = get_goodbye_channel(member.guild)
        if channel:
            embed = discord.Embed(title=f"ยินดีต้อนรับ {member.display_name} 🎉", description=f"เข้าดิส **{member.guild.name}** แล้ว\nสมาชิกตอนนี้ {member.guild.member_count} คน\nพิมพ์ `!rank` เช็คเวล | `!roles` รับยศเกม", color=0x00ff00)
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"ID: {member.id}")
            await channel.send(embed=embed)
    except Exception as e:
        print(f"Welcome error: {e}")

@bot.event
async def on_member_remove(member):
    try:
        channel = get_goodbye_channel(member.guild)
        if channel:
            embed = discord.Embed(title=f"{member.display_name} ออกจากดิสแล้ว 👋", description=f"เหลือสมาชิก {member.guild.member_count} คน", color=0xff0000)
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"ID: {member.id}")
            await channel.send(embed=embed)
    except Exception as e:
        print(f"Goodbye error: {e}")

@bot.event
async def on_message_delete(message):
    try:
        if message.author.bot or not message.guild:
            return
        channel = get_log_channel(message.guild)
        if not channel:
            return
        embed = discord.Embed(title="🗑️ ลบข้อความ", color=0xff0000, timestamp=discord.utils.utcnow())
        embed.add_field(name="คนส่ง", value=f"{message.author.mention} ({message.author})", inline=False)
        embed.add_field(name="ห้อง", value=message.channel.mention, inline=True)
        content = message.content or "*ไม่มีข้อความ (อาจเป็นรูป/ไฟล์)*"
        if len(content) > 1000:
            content = content[:1000] + "..."
        embed.add_field(name="ข้อความ", value=content, inline=False)
        embed.set_footer(text=f"ID: {message.author.id}")
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Log delete error: {e}")

@bot.event
async def on_message_edit(before, after):
    try:
        if before.author.bot or not before.guild or before.content == after.content:
            return
        channel = get_log_channel(before.guild)
        if not channel:
            return
        embed = discord.Embed(title="✏️ แก้ไขข้อความ", color=0xffa500, timestamp=discord.utils.utcnow())
        embed.add_field(name="คนส่ง", value=f"{before.author.mention}", inline=False)
        embed.add_field(name="ห้อง", value=before.channel.mention, inline=True)
        embed.add_field(name="ก่อน", value=(before.content[:500] or "*ว่าง*"), inline=False)
        embed.add_field(name="หลัง", value=(after.content[:500] or "*ว่าง*"), inline=False)
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Log edit error: {e}")

@bot.event
async def on_message(message):
    try:
        if message.author.bot:
            await bot.process_commands(message)
            return
        # --- ระบบเวล: ให้ XP ทุกข้อความ ---
        if message.guild:
            try:
                uid = message.author.id
                xp_data[uid] += random.randint(10, 20)
                new_level = get_level(xp_data[uid])
                if new_level > level_data[uid]:
                    level_data[uid] = new_level
                    save_xp()
                    try:
                        await message.channel.send(f"🎉 {message.author.mention} เลเวลอัพเป็น **เวล {new_level}** แล้ว! (XP: {xp_data[uid]})")
                    except: pass
                # เซฟทุก 10 ข้อความ
                if random.random() < 0.1:
                    save_xp()
            except Exception as e:
                print(f"XP error: {e}")
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
                except: pass
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
                except: pass
        await bot.process_commands(message)
    except Exception as e:
        print(f"on_message error: {e}")
        try: await bot.process_commands(message)
        except: pass

# ===== คำสั่งเวล =====
@bot.command(name="rank")
async def rank(ctx, member: discord.Member = None):
    try:
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
    except Exception as e:
        await ctx.send(f"❌ {e}")

@bot.command(name="top")
async def top(ctx):
    try:
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
    except Exception as e:
        await ctx.send(f"❌ {e}")

@bot.command(name="addxp")
@is_admin()
async def addxp(ctx, member: discord.Member, amount: int):
    try:
        xp_data[member.id] += amount
        lv = get_level(xp_data[member.id])
        level_data[member.id] = lv
        save_xp()
        await ctx.send(f"✅ เพิ่ม {amount} XP ให้ {member.mention} แล้ว → ตอนนี้เวล {lv} ({xp_data[member.id]} XP)")
    except Exception as e:
        await ctx.send(f"❌ {e}")

@bot.command(name="addlevel")
@is_admin()
async def addlevel(ctx, member: discord.Member, level: int):
    try:
        target_xp = level * 150
        xp_data[member.id] = target_xp
        level_data[member.id] = level
        save_xp()
        await ctx.send(f"✅ ตั้ง {member.mention} เป็นเวล {level} แล้ว ({target_xp} XP)")
    except Exception as e:
        await ctx.send(f"❌ {e}")

# ===== ปุ่มรับยศ =====
@bot.command(name="roles")
@is_admin()
async def roles(ctx):
    try:
        embed = discord.Embed(title="กดรับยศเกม 🎮", description="กดปุ่มด้านล่างเพื่อรับยศเกมที่เล่น\nกดอีกทีเพื่อลบยศออก", color=0x9b59b6)
        await ctx.send(embed=embed, view=GameRoleView())
    except Exception as e:
        await ctx.send(f"❌ {e}")

# ===== Giveaway =====
class GiveawayView(discord.ui.View):
    def __init__(self, prize):
        super().__init__(timeout=None)
        self.prize = prize
        self.users = set()
    @discord.ui.button(label="🎉 เข้าร่วม", style=discord.ButtonStyle.green, custom_id="giveaway_join")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.users:
            await interaction.response.send_message("คุณเข้าร่วมแล้ว!", ephemeral=True)
        else:
            self.users.add(interaction.user.id)
            await interaction.response.send_message(f"✅ เข้าร่วม Giveaway **{self.prize}** แล้ว! ({len(self.users)} คน)", ephemeral=True)

def parse_duration(s):
    try:
        s = s.lower().strip()
        if s.endswith("s"): return int(s[:-1])
        if s.endswith("m"): return int(s[:-1])*60
        if s.endswith("h"): return int(s[:-1])*3600
        if s.endswith("d"): return int(s[:-1])*86400
        return int(s)
    except: return 60

@bot.command(name="giveaway")
@is_admin()
async def giveaway(ctx, duration: str = "60s", *, prize: str = "รางวัล"):
    try:
        sec = parse_duration(duration)
        if sec < 5: sec = 5
        if sec > 86400: sec = 86400
        view = GiveawayView(prize)
        embed = discord.Embed(title=f"🎉 Giveaway: {prize}", description=f"กดปุ่ม **เข้าร่วม** ด้านล่าง\nจบใน **{duration}** ({sec} วินาที)\nพิมพ์โดย {ctx.author.mention}", color=0xffd700, timestamp=discord.utils.utcnow() + datetime.timedelta(seconds=sec))
        embed.set_footer(text=f"จัดโดย {ctx.author.display_name}")
        msg = await ctx.send(embed=embed, view=view)
        await asyncio.sleep(sec)
        if not view.users:
            await ctx.send(f"😢 Giveaway **{prize}** จบแล้ว ไม่มีคนเข้าร่วมเลย")
            try: await msg.edit(view=None)
            except: pass
            return
        winner_id = random.choice(list(view.users))
        winner = ctx.guild.get_member(winner_id)
        mention = winner.mention if winner else f"<@{winner_id}>"
        await ctx.send(f"🎉 Giveaway **{prize}** จบแล้ว! ผู้โชคดีคือ {mention} 🎊")
        try: await msg.edit(view=None)
        except: pass
    except Exception as e:
        await ctx.send(f"❌ {e}\nใช้: `!giveaway 10m Nitro` หรือ `!giveaway 60s ของรางวัล`")

# ===== มีม + สุ่ม =====
@bot.command(name="meme")
async def meme(ctx):
    try:
        memes = ["https://i.imgflip.com/65efzo.jpg","https://i.imgflip.com/26am.jpg","https://i.imgflip.com/1bij.jpg","https://i.imgflip.com/1g8my4.jpg"]
        embed = discord.Embed(title="มีม GenZ 😂", color=0xf1c40f)
        embed.set_image(url=random.choice(memes))
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ {e}")

@bot.command(name="สุ่ม")
async def random_cmd(ctx, *, choices: str = None):
    try:
        if not choices:
            await ctx.send("ใช้: `!สุ่ม พิซซ่า ชาบู หมูกระทะ`")
            return
        items = [c.strip() for c in choices.replace(",", " ").split() if c.strip()]
        await ctx.send(f"🎲 สุ่มได้: **{random.choice(items)}**")
    except Exception as e:
        await ctx.send(f"❌ {e}")

# ===== คำสั่งเดิม (มี try ทั้งหมด) =====
@bot.command(name="antispam")
@is_admin()
async def antispam(ctx, mode: str = None):
    try:
        if mode == "on":
            antispam_enabled[ctx.guild.id] = True
            await ctx.send("✅ เปิดระบบกันสแปมแล้ว (5 ข้อความ/5วิ = mute 60วิ + กันลิงก์ discord.gg)")
        elif mode == "off":
            antispam_enabled[ctx.guild.id] = False
            await ctx.send("❌ ปิดระบบกันสแปมแล้ว")
        else:
            status = "เปิด ✅" if antispam_enabled[ctx.guild.id] else "ปิด ❌"
            await ctx.send(f"สถานะกันสแปมตอนนี้: {status}\nใช้ `!antispam on` หรือ `!antispam off`")
    except Exception as e:
        await ctx.send(f"❌ {e}")

@bot.command(name="setspam")
@is_admin()
async def setspam(ctx, limit: int = None, seconds: int = None, mute: int = None):
    global SPAM_LIMIT, SPAM_TIME, MUTE_TIME
    try:
        if limit is None:
            await ctx.send(f"ตั้งค่าปัจจุบัน: `{SPAM_LIMIT} ข้อความ / {SPAM_TIME} วินาที = mute {MUTE_TIME} วิ`\nใช้: `!setspam จำนวนข้อความ วินาที เวลาmute` เช่น `!setspam 5 5 120`")
            return
        SPAM_LIMIT = limit
        if seconds: SPAM_TIME = seconds
        if mute: MUTE_TIME = mute
        await ctx.send(f"✅ ตั้งค่าใหม่แล้ว: `{SPAM_LIMIT} ข้อความ / {SPAM_TIME} วิ = mute {MUTE_TIME} วิ` + ลบข้อความย้อนหลังทั้งหมด")
    except Exception as e:
        await ctx.send(f"❌ {e}")

@bot.command(name="clear")
@is_admin()
async def clear(ctx, amount: int = 10):
    try:
        if amount > 100:
            await ctx.send("ลบได้ครั้งละไม่เกิน 100 ข้อความครับ")
            return
        deleted = await ctx.channel.purge(limit=amount+1)
        await ctx.send(f"ลบไป {len(deleted)-1} ข้อความแล้ว ✅", delete_after=5)
    except Exception as e:
        await ctx.send(f"❌ {e}")

@bot.command(name="create-channel")
@is_admin()
async def create_channel(ctx, *, name: str):
    try:
        await ctx.guild.create_text_channel(name)
        await ctx.send(f"สร้างห้อง `{name}` สำเร็จ ✅")
    except Exception as e:
        await ctx.send(f"❌ {e}")

@bot.command(name="delete-channel")
@is_admin()
async def delete_channel(ctx, channel: discord.TextChannel):
    try:
        await ctx.send(f"คุณต้องการลบห้อง {channel.mention} จริงๆใช่มั้ย? พิมพ์ `ยืนยัน` ภายใน 15 วินาที")
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content == "ยืนยัน"
        await bot.wait_for('message', check=check, timeout=15.0)
        await channel.delete(reason=f"ลบโดย {ctx.author}")
        await ctx.send(f"ลบห้อง {channel.name} แล้ว ✅")
    except asyncio.TimeoutError:
        await ctx.send("ยกเลิกการลบ ❌ (หมดเวลา/ไม่ได้พิมพ์ยืนยัน)")
    except Exception as e:
        await ctx.send(f"❌ {e}")

@bot.command(name="backup")
@is_admin()
async def backup(ctx):
    try:
        data = {"guild": ctx.guild.name, "channels": [c.name for c in ctx.guild.channels], "roles": [r.name for r in ctx.guild.roles]}
        with open(f"backup_{ctx.guild.id}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        await ctx.send("Backup เสร็จแล้ว ✅ ได้ไฟล์ `backup_...json`", file=discord.File(f"backup_{ctx.guild.id}.json"))
    except Exception as e:
        await ctx.send(f"❌ {e}")

# รันบอท
TOKEN = os.getenv("DISCORD_TOKEN") or "ใส่_TOKEN_ใหม่ตรงนี้"
bot.run(TOKEN)
