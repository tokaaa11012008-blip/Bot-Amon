import discord
from discord.ext import commands, tasks
import json
import os
import random
import psycopg2
from psycopg2.extras import RealDictCursor
class Level(commands.Cog):
    def __init__(self, bot):
        self.bt = obot

    # =================================================================
    # 📡 1. CẤU HÌNH CƠ BẢN & KẾT NỐI POSTGRESQL
    # =================================================================
    TOKEN = os.getenv("BOT_TOKEN") 
    # Railway tự động cung cấp biến DATABASE_URL khi bạn add Postgres vào dự án
    DATABASE_URL = os.getenv("DATABASE_URL") 

    PREFIX = "f"
    BACKUP_LEVELS_FILE = "backup_levels.json"
    BACKUP_CONFIG_FILE = "backup_config.json"

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.voice_states = True

    bot = commands.Bot(command_prefix=PREFIX, intents=intents)

    def get_db_connection():
        """Tạo kết nối tới cơ sở dữ liệu PostgreSQL trên Railway"""
        return psycopg2.connect(DATABASE_URL, sslmode="require")

    # =================================================================
    # 🗄️ 2. KHỞI TẠO BẢNG CƠ SỞ DỮ LIỆU (DATABASE INITIALIZATION)
    # =================================================================
    def init_db():
        """Tạo các bảng cần thiết nếu chưa tồn tại"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Bảng lưu trữ cấp độ người dùng
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_levels (
                guild_id VARCHAR(50),
                user_id VARCHAR(50),
                text_xp INT DEFAULT 0,
                text_level INT DEFAULT 1,
                voice_xp INT DEFAULT 0,
                voice_level INT DEFAULT 1,
                PRIMARY KEY (guild_id, user_id)
            );
        """)
        
        # Bảng lưu cấu hình máy chủ (Kênh log, role thưởng, boost)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id VARCHAR(50) PRIMARY KEY,
                log_channel VARCHAR(50) DEFAULT NULL,
                text_rewards JSONB DEFAULT '{}'::jsonb,
                voice_rewards JSONB DEFAULT '{}'::jsonb,
                boost_roles JSONB DEFAULT '{}'::jsonb
            );
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        print("➔ [Database] Khởi tạo cấu trúc bảng thành công.")

    # Khởi tạo DB ngay khi chạy script
    if DATABASE_URL:
        init_db()
    else:
        print("⚠️ CẢNH BÁO: Chưa tìm thấy biến DATABASE_URL. Hệ thống DB Postgres sẽ không hoạt động!")

    # =================================================================
    # 💾 3. HÀM TƯƠNG TÁC DB & ĐỒNG BỘ BACKUP
    # =================================================================
    def db_get_user(guild_id, user_id):
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM user_levels WHERE guild_id = %s AND user_id = %s;", (str(guild_id), str(user_id)))
        user = cur.fetchone()
        
        if not user:
            cur.execute(
                "INSERT INTO user_levels (guild_id, user_id) VALUES (%s, %s) RETURNING *;", 
                (str(guild_id), str(user_id))
            )
            user = cur.fetchone()
            conn.commit()
            
        cur.close()
        conn.close()
        return dict(user)

    def db_update_user(guild_id, user_id, text_xp, text_level, voice_xp, voice_level):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE user_levels 
            SET text_xp = %s, text_level = %s, voice_xp = %s, voice_level = %s
            WHERE guild_id = %s AND user_id = %s;
        """, (text_xp, text_level, voice_xp, voice_level, str(guild_id), str(user_id)))
        conn.commit()
        cur.close()
        conn.close()

    def db_get_config(guild_id):
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM guild_config WHERE guild_id = %s;", (str(guild_id),))
        cfg = cur.fetchone()
        
        if not cfg:
            cur.execute("INSERT INTO guild_config (guild_id) VALUES (%s) RETURNING *;", (str(guild_id),))
            cfg = cur.fetchone()
            conn.commit()
            
        cur.close()
        conn.close()
        return dict(cfg)

    def db_update_config(guild_id, key, value):
        """Cập nhật các trường cấu hình động (Hỗ trợ định dạng JSONB)"""
        conn = get_db_connection()
        cur = conn.cursor()
        if key in ["text_rewards", "voice_rewards", "boost_roles"]:
            cur.execute(f"UPDATE guild_config SET {key} = %s WHERE guild_id = %s;", (json.dumps(value), str(guild_id)))
        else:
            cur.execute(f"UPDATE guild_config SET {key} = %s WHERE guild_id = %s;", (value, str(guild_id)))
        conn.commit()
        cur.close()
        conn.close()

    # =================================================================
    # 🕒 4. LOOP TỰ ĐỘNG SAO LƯU DỮ LIỆU (AUTO-BACKUP TO JSON)
    # =================================================================
    @tasks.loop(hours=2.0)
    async def auto_backup_to_json():
        """Cứ mỗi 2 giờ, Bot tải toàn bộ dữ liệu Postgres về lưu vào file JSON dự phòng đề phòng sự cố"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 1. Backup bảng levels
            cur.execute("SELECT * FROM user_levels;")
            levels_rows = cur.fetchall()
            levels_backup = {}
            for row in levels_rows:
                g = row['guild_id']
                u = row['user_id']
                if g not in levels_backup: levels_backup[g] = {}
                levels_backup[g][u] = {
                    "text_xp": row['text_xp'], "text_level": row['text_level'],
                    "voice_xp": row['voice_xp'], "voice_level": row['voice_level']
                }
            with open(BACKUP_LEVELS_FILE, "w", encoding="utf-8") as f:
                json.dump(levels_backup, f, indent=4, ensure_ascii=False)
                
            # 2. Backup bảng config
            cur.execute("SELECT * FROM guild_config;")
            config_rows = cur.fetchall()
            config_backup = {}
            for row in config_rows:
                config_backup[row['guild_id']] = {
                    "log_channel": row['log_channel'],
                    "text_rewards": row['text_rewards'],
                    "voice_rewards": row['voice_rewards'],
                    "boost_roles": row['boost_roles']
                }
            with open(BACKUP_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_backup, f, indent=4, ensure_ascii=False)
                
            cur.close()
            conn.close()
            print("💾 [Backup] Đã sao lưu toàn bộ dữ liệu từ Postgres vào các tệp JSON cục bộ.")
        except Exception as e:
            print(f"❌ [Backup] Lỗi trong quá trình tự động sao lưu: {e}")

    # =================================================================
    # ⚙️ 5. CÔNG THỨC LEVEL & MỨC BOOST ROLE
    # =================================================================
    def xp_for_next_level(level):
        return 15* ( level ** 2 )

    def get_xp_multiplier(member):
        if isinstance(member, discord.User) or not member.guild:
            return 1.0
            
        config = db_get_config(member.guild.id)
        boost_roles = config.get("boost_roles", {})
        multiplier = 1.0
        
        for role in member.roles:
            if str(role.id) in boost_roles:
                role_multiplier = float(boost_roles[str(role.id)])
                if role_multiplier > multiplier:
                    multiplier = role_multiplier
        return multiplier

    # =================================================================
    # 🎉 6. LOGIC XỬ LÝ LÊN CẤP & AUTO ADD ROLE THƯỞNG
    # =================================================================
    async def handle_level_up(member, new_level, level_type):
        config = db_get_config(member.guild.id)
        reward_key = "text_rewards" if level_type == "text" else "voice_rewards"
        rewards = config.get(reward_key, {})
        
        role_msg = ""
        if str(new_level) in rewards:
            role_id = rewards[str(new_level)]
            role = member.guild.get_role(int(role_id))
            if role:
                try:
                    await member.add_roles(role)
                    role_msg = f"\n🎁 Bạn đã được cấp Rank Role: **{role.name}**"
                except discord.Forbidden:
                    role_msg = f"\n⚠️ Bot thiếu quyền để trao Role: **{role.name}**"
                except Exception:
                    role_msg = f"\n⚠️ Đã xảy ra lỗi khi tự động gán Role **{role.name}**"

        channel_id = config.get("log_channel")
        if channel_id:
            channel = member.guild.get_channel(int(channel_id))
            if channel:
                type_str = "💬 CHAT " if level_type == "text" else "🎙️ VOICE"
                embed = discord.Embed(
                    title="🎉 CHÚC MỪNG BẠN LÊN CẤP MỚI!",
                    description=f"{member.mention} vừa đạt đến **Level {new_level}** ở **{type_str}**!{role_msg}",
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                try:
                    await channel.send(content=member.mention, embed=embed)
                except:
                    pass

    # =================================================================
    # 🕒 7. SỰ KIỆN KHỞI ĐỘNG & TÍNH XP ĐỘNG (LƯU TRỮ VÀO DATABASE)
    # =================================================================
    @bot.event
    async def on_ready():
        print(f"=== Bot Level Đã Sẵn Sàng ===")
        print(f"Tên Bot: {bot.user}")
        if not voice_xp_counter.is_running():
            voice_xp_counter.start()
        if not auto_backup_to_json.is_running():
            auto_backup_to_json.start()

    @bot.event
    async def on_message(message):
        if message.author.bot or not message.guild:
            return

        u_data = db_get_user(message.guild.id, message.author.id)
        
        base_xp = random.randint(15, 25)
        multiplier = get_xp_multiplier(message.author)
        xp_to_add = int(base_xp * multiplier)
        
        u_data["text_xp"] += xp_to_add
        current_lv = u_data["text_level"]
        xp_needed = xp_for_next_level(current_lv)
        
        while u_data["text_xp"] >= xp_needed:
            u_data["text_xp"] -= xp_needed
            u_data["text_level"] += 1
            await handle_level_up(message.author, u_data["text_level"], "text")
            current_lv = u_data["text_level"]
            xp_needed = xp_for_next_level(current_lv)

        db_update_user(message.guild.id, message.author.id, u_data["text_xp"], u_data["text_level"], u_data["voice_xp"], u_data["voice_level"])
        await bot.process_commands(message)

    @tasks.loop(minutes=2.5)
    async def voice_xp_counter():
        for guild in bot.guilds:
            for voice_channel in guild.voice_channels:
                members = [m for m in voice_channel.members if not m.bot and not (m.voice.self_deaf or m.voice.deaf)]
                if len(members) < 1: 
                    continue
                    
                for member in members:
                    u_data = db_get_user(guild.id, member.id)
                    
                    base_xp = random.randint(20, 30)
                    multiplier = get_xp_multiplier(member)
                    xp_to_add = int(base_xp * multiplier)
                    
                    u_data["voice_xp"] += xp_to_add
                    current_lv = u_data["voice_level"]
                    xp_needed = xp_for_next_level(current_lv)
                    
                    while u_data["voice_xp"] >= xp_needed:
                        u_data["voice_xp"] -= xp_needed
                        u_data["voice_level"] += 1
                        await handle_level_up(member, u_data["voice_level"], "voice")
                        current_lv = u_data["voice_level"]
                        xp_needed = xp_for_next_level(current_lv)
                        
                    db_update_user(guild.id, member.id, u_data["text_xp"], u_data["text_level"], u_data["voice_xp"], u_data["voice_level"])

    # =================================================================
    # 📊 8. HỆ THỐNG LỆNH NGƯỜI DÙNG (USER COMMANDS)
    # =================================================================
    @bot.command(name="rank")
    async def rank(ctx, member: discord.Member = None):
        member = member or ctx.author
        u_data = db_get_user(ctx.guild.id, member.id)
        
        t_xp, t_lv = u_data["text_xp"], u_data["text_level"]
        t_next = xp_for_next_level(t_lv)
        
        v_xp, v_lv = u_data["voice_xp"], u_data["voice_level"]
        v_next = xp_for_next_level(v_lv)
        
        def make_progress_bar(xp, next_xp):
            filled_bars = int((xp / next_xp) * 10)
            return "▰" * filled_bars + "▱" * (10 - filled_bars)

        embed = discord.Embed(title=f"💳 THẺ LEVEL - {member.display_name}", color=discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.add_field(
            name="💬 Text Level", 
            value=f"**Cấp độ:** {t_lv}\n**Kinh nghiệm:** {t_xp}/{t_next} XP\n{make_progress_bar(t_xp, t_next)}", 
            inline=False
        )
        embed.add_field(
            name="🎤 Voice Level", 
            value=f"**Cấp độ:** {v_lv}\n**Kinh nghiệm:** {v_xp}/{v_next} XP\n{make_progress_bar(v_xp, v_next)}", 
            inline=False
        )
        
        multiplier = get_xp_multiplier(member)
        boost_text = "Mặc định (0%)" if multiplier == 1.0 else f"+{int((multiplier - 1.0) * 100)}% XP Boost"

        embed.set_footer(text=f"Tốc độ nhận XP của bạn: {boost_text}")
        await ctx.send(embed=embed)

    @bot.command(name="top")
    async def leaderboard(ctx, type: str = "text"):
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        type_lower = type.lower()
        
        if type_lower == "text":
            title = "💬 BẢNG XẾP HẠNG TOP TEXT LEVEL"
            cur.execute("SELECT user_id, text_level, text_xp FROM user_levels WHERE guild_id = %s ORDER BY text_level DESC, text_xp DESC LIMIT 10;", (str(ctx.guild.id),))
            rows = cur.fetchall()
            line_format = lambda r: f"Cấp {r['text_level']} ({r['text_xp']} XP)"
        elif type_lower == "voice":
            title = "🎤 BẢNG XẾP HẠNG TOP VOICE LEVEL"
            cur.execute("SELECT user_id, voice_level, voice_xp FROM user_levels WHERE guild_id = %s ORDER BY voice_level DESC, voice_xp DESC LIMIT 10;", (str(ctx.guild.id),))
            rows = cur.fetchall()
            line_format = lambda r: f"Cấp {r['voice_level']} ({r['voice_xp']} XP)"
        elif type_lower in ["xp", "total"]:
            title = "⭐ BẢNG XẾP HẠNG TỔNG HỢP TOÀN BỘ XP"
            cur.execute("""
                SELECT user_id, text_level, voice_level 
                FROM user_levels WHERE guild_id = %s 
                ORDER BY ((text_level ^ 2) * 100 + text_xp + (voice_level ^ 2) * 100 + voice_xp) DESC LIMIT 10;
            """, (str(ctx.guild.id),))
            rows = cur.fetchall()
            line_format = lambda r: f"Text: Lv.{r['text_level']} | Voice: Lv.{r['voice_level']}"
        else:
            cur.close()
            conn.close()
            return await ctx.send("❌ Sai cú pháp! Vui lòng chọn đúng loại: `f!top text`, `f!top voice` hoặc `f!top xp`")

        cur.close()
        conn.close()

        if not rows:
            return await ctx.send("❌ Server chưa có dữ liệu bảng xếp hạng.")

        embed = discord.Embed(title=title, color=discord.Color.gold(), description="")
        for index, row in enumerate(rows, 1):
            member = ctx.guild.get_member(int(row['user_id']))
            name = member.display_name if member else f"Thành viên cũ ({row['user_id']})"
            embed.description += f"**#{index}** | {name} ➔ {line_format(row)}\n"
            
        await ctx.send(embed=embed)

    # =================================================================
    # 🛠️ 9. NHÓM LỆNH SỬA ĐIỂM THỦ CÔNG (ADMIN ONLY)
    # =================================================================
    @bot.command(name="managexp")
    @commands.has_permissions(administrator=True)
    async def manage_xp(ctx, action: str, type: str, member: discord.Member, amount: int):
        if amount <= 0: return await ctx.send("❌ Số lượng XP phải lớn hơn 0.")
        
        u_data = db_get_user(ctx.guild.id, member.id)
        target_key = f"{type.lower()}_xp"
        if target_key not in ["text_xp", "voice_xp"]:
            return await ctx.send("❌ Loại hình không hợp lệ. Hãy chọn `text` hoặc `voice`.")
            
        action_lower = action.lower()
        if action_lower == "add":
            u_data[target_key] += amount
            msg = f"✅ Đã cộng thêm **{amount} XP {type.upper()}** cho {member.mention}."
            
            level_key = "text_level" if type.lower() == "text" else "voice_level"
            current_lv = u_data[level_key]
            xp_needed = xp_for_next_level(current_lv)
            while u_data[target_key] >= xp_needed:
                u_data[target_key] -= xp_needed
                u_data[level_key] += 1
                await handle_level_up(member, u_data[level_key], type.lower())
                current_lv = u_data[level_key]
                xp_needed = xp_for_next_level(current_lv)
                
        elif action_lower == "remove":
            u_data[target_key] = max(0, u_data[target_key] - amount)
            msg = f"✅ Đã khấu trừ **{amount} XP {type.upper()}** của {member.mention}."
        else:
            return await ctx.send("❌ Hành động sai. Hãy nhập rõ `add` hoặc `remove`.")
            
        db_update_user(ctx.guild.id, member.id, u_data["text_xp"], u_data["text_level"], u_data["voice_xp"], u_data["voice_level"])
        await ctx.send(msg)

    @bot.command(name="managelevel")
    @commands.has_permissions(administrator=True)
    async def manage_level(ctx, action: str, type: str, member: discord.Member, amount: int):
        if amount <= 0: return await ctx.send("❌ Số lượng cấp độ phải lớn hơn 0.")
        u_data = db_get_user(ctx.guild.id, member.id)
        
        target_key = f"{type.lower()}_level"
        if target_key not in ["text_level", "voice_level"]:
            return await ctx.send("❌ Loại hình không hợp lệ. Hãy chọn `text` hoặc `voice`.")
            
        action_lower = action.lower()
        if action_lower == "add":
            u_data[target_key] += amount
            msg = f"✅ Đã tăng thêm **{amount} Cấp {type.upper()}** cho {member.mention}."
        elif action_lower == "remove":
            u_data[target_key] = max(1, u_data[target_key] - amount)
            msg = f"✅ Đã hạ xuống **{amount} Cấp {type.upper()}** của {member.mention}."
        else:
            return await ctx.send("❌ Hành động sai. Hãy nhập rõ `add` hoặc `remove`.")
            
        db_update_user(ctx.guild.id, member.id, u_data["text_xp"], u_data["text_level"], u_data["voice_xp"], u_data["voice_level"])
        await ctx.send(msg)

    # =================================================================
    # ⚙️ 10. NHÓM LỆNH CÀI ĐẶT HỆ THỐNG (ADMIN ONLY)
    # =================================================================
    @bot.command(name="setchannel")
    @commands.has_permissions(administrator=True)
    async def set_channel(ctx, channel: discord.TextChannel):
        db_update_config(ctx.guild.id, "log_channel", str(channel.id))
        await ctx.send(f"✅ Đã đặt kênh thông báo lên cấp của máy chủ thành: {channel.mention}")

    @bot.command(name="addreward")
    @commands.has_permissions(administrator=True)
    async def add_reward(ctx, type: str, level: int, role: discord.Role):
        type_lower = type.lower()
        if type_lower not in ["text", "voice"]: 
            return await ctx.send("❌ Vui lòng phân loại chính xác hệ thống: `text` hoặc `voice`!")
        if level <= 0: return await ctx.send("❌ Cấp độ nhận thưởng phải lớn hơn 0.")
            
        config = db_get_config(ctx.guild.id)
        reward_key = "text_rewards" if type_lower == "text" else "voice_rewards"
        
        rewards = config.get(reward_key, {})
        rewards[str(level)] = str(role.id)
        
        db_update_config(ctx.guild.id, reward_key, rewards)
        await ctx.send(f"✅ Đã lưu cài đặt: Khi đạt **{type_lower.upper()} Level {level}** ➔ Tự động trao vai trò {role.mention}")

    @bot.command(name="removereward")
    @commands.has_permissions(administrator=True)
    async def remove_reward(ctx, type: str, level: int):
        type_lower = type.lower()
        if type_lower not in ["text", "voice"]: return await ctx.send("❌ Vui lòng chọn loại: `text` hoặc `voice`!")
            
        config = db_get_config(ctx.guild.id)
        reward_key = "text_rewards" if type_lower == "text" else "voice_rewards"
        rewards = config.get(reward_key, {})
        
        if str(level) in rewards:
            del rewards[str(level)]
            db_update_config(ctx.guild.id, reward_key, rewards)
            await ctx.send(f"✅ Đã hủy bỏ phần thưởng Role cho mốc **{type_lower.upper()} Level {level}**.")
        else:
            await ctx.send("❌ Không tìm thấy phần thưởng Role nào được thiết lập ở mốc cấp độ này.")

    # =================================================================
    # ⚡ 11. NHÓM LỆNH QUẢN LÝ BOOST ROLE ĐỘNG
    # =================================================================
    @bot.command(name="addboost")
    @commands.has_permissions(administrator=True)
    async def add_boost(ctx, role: discord.Role, multiplier: float):
        if multiplier <= 0: return await ctx.send("❌ Hệ số nhân XP phải lớn hơn 0!")
            
        config = db_get_config(ctx.guild.id)
        boost_roles = config.get("boost_roles", {})
        boost_roles[str(role.id)] = multiplier
        
        db_update_config(ctx.guild.id, "boost_roles", boost_roles)
        show_pct = int((multiplier - 1.0) * 100)
        await ctx.send(f"✅ Đã thiết lập Role Boost: {role.mention} ➔ **{'+' if show_pct >= 0 else ''}{show_pct}%** tốc độ cày XP!")

    @bot.command(name="removeboost")
    @commands.has_permissions(administrator=True)
    async def remove_boost(ctx, role: discord.Role):
        config = db_get_config(ctx.guild.id)
        boost_roles = config.get("boost_roles", {})
        
        if str(role.id) in boost_roles:
            del boost_roles[str(role.id)]
            db_update_config(ctx.guild.id, "boost_roles", boost_roles)
            await ctx.send(f"✅ Đã xóa quyền tăng tốc XP của Role **{role.name}**.")
        else:
            await ctx.send("❌ Role này chưa được thiết lập làm Role Boost.")

    @bot.command(name="settings")
    async def show_settings(ctx):
        data = db_get_config(ctx.guild.id)
        log_channel = ctx.guild.get_channel(int(data.get("log_channel"))) if data.get("log_channel") else None
        
        embed = discord.Embed(title=f"⚙️ BẢNG CẤU HÌNH HỆ THỐNG LEVEL - {ctx.guild.name}", color=discord.Color.blue())
        embed.add_field(name="📡 Kênh thông báo lên cấp", value=log_channel.mention if log_channel else "Chưa cài đặt", inline=False)
        
        t_rewards = "\n".join([f"• Level {lv}: <@&{rid}>" for lv, rid in data.get("text_rewards", {}).items()])
        v_rewards = "\n".join([f"• Level {lv}: <@&{rid}>" for lv, rid in data.get("voice_rewards", {}).items()])
        
        boost_roles_data = data.get("boost_roles", {})
        b_roles_list = []
        for rid, multi in boost_roles_data.items():
            pct = int((float(multi) - 1.0) * 100)
            b_roles_list.append(f"• <@&{rid}>: **{'+' if pct >= 0 else ''}{pct}%** XP")
        b_roles = "\n".join(b_roles_list)
        
        embed.add_field(name="💬 Vai trò thưởng khi Chat Text", value=t_rewards or "_Chưa thiết lập mốc nào_", inline=True)
        embed.add_field(name="🎙️ Vai trò thưởng khi Nói Voice", value=v_rewards or "_Chưa thiết lập mốc nào_", inline=True)
        embed.add_field(name="⚡ Vai trò Boost XP Đang Chạy", value=b_roles or "_Chưa có role tăng tốc nào_", inline=False)
        await ctx.send(embed=embed)

    # =================================================================
    # ⚠️ 12. BÁO LỖI QUYỀN HẠN & KHỞI CHẠY BOT
    # =================================================================
    @manage_xp.error
    @manage_level.error
    @set_channel.error
    @add_reward.error
    @remove_reward.error
    @add_boost.error
    @remove_boost.error
    async def permissions_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Bạn không có quyền `Administrator` để thực hiện cấu hình này!")


async def level(bot):
    await bot.add_cog(Level(bot))