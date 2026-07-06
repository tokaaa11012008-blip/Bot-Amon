import discord
from discord.ext import commands
import datetime

class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_log_channel(self, guild_id: str):
        try:
            async with self.bot.db.acquire() as conn:
                return await conn.fetchval('SELECT log_channel_id FROM server_config WHERE guild_id = $1', guild_id)
        except: return None

    async def send_log(self, guild: discord.Guild, embed: discord.Embed):
        if not guild: return
        log_channel_id = await self.get_log_channel(str(guild.id))
        if log_channel_id:
            channel = self.bot.get_channel(log_channel_id)
            if channel: await channel.send(embed=embed)

    # ==========================================
    # 1. MESSAGE LOGS (Nhật ký tin nhắn)
    # ==========================================
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or message.guild is None: return
        embed = discord.Embed(title="»»» Có tên nào đó đã trộm đi 1 câu nói của kẻ khác", color=discord.Color.red(), timestamp=datetime.datetime.now())
        embed.add_field(name="Bản thể bị trộm :", value=message.author.mention, inline=True)
        embed.add_field(name="Nơi bị trộm :", value=message.channel.mention, inline=True)
        embed.add_field(name="Câu nói :", value=message.content or "[Không có văn bản/Tin nhắn chứa ảnh]", inline=False)
        await self.send_log(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.content == after.content or before.guild is None: return
        embed = discord.Embed(title="«‹«« Hắn vừa thay đổi khái niệm bằng quyền năng trộm được »›»»", color=discord.Color.orange(), timestamp=datetime.datetime.now())
        embed.add_field(name="Kẻ thực hiện:", value=before.author.mention, inline=False)
        embed.add_field(name="Cựu khái niệm :", value=before.content, inline=True)
        embed.add_field(name="Sau khi thay đổi:", value=after.content, inline=True)
        await self.send_log(before.guild, embed)

    # ==========================================
    # 2. MEMBER LOGS (Nhật ký thành viên nội bộ)
    # ==========================================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = discord.Embed(title="🚪 Một ký sinh trùng mới rơi vào dòng thời gian", color=discord.Color.green(), timestamp=datetime.datetime.now())
        embed.add_field(name="Tên cá thể:", value=f"{member.mention} ({member.name})", inline=True)
        embed.add_field(name="ID bản thể:", value=member.id, inline=True)
        embed.add_field(name="Thọ mệnh thời gian chi trùng:", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=False)
        if member.avatar: embed.set_thumbnail(url=member.avatar.url)
        await self.send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        embed = discord.Embed(title="🚪 Một con trùng đã tan biến hoặc bị trục xuất", color=discord.Color.dark_grey(), timestamp=datetime.datetime.now())
        embed.add_field(name="Cá thể rời đi:", value=f"{member.name}#{member.discriminator if hasattr(member, 'discriminator') else ''} ({member.id})", inline=False)
        await self.send_log(member.guild, embed)

    # ==========================================
    # 2 & 3. MEMBER & USER LOGS (Cập nhật Hồ Sơ Hoàn Chỉnh)
    # ==========================================
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # A. Hồ sơ máy chủ: Thay đổi Biệt danh (Nickname)
        if before.nick != after.nick:
            embed = discord.Embed(title="🎭 Thay đổi ký hiệu danh tính (Nickname)", color=discord.Color.blue(), timestamp=datetime.datetime.now())
            embed.add_field(name="Bản thể:", value=after.mention, inline=False)
            embed.add_field(name="Ký danh cũ:", value=before.nick or "Không có", inline=True)
            embed.add_field(name="Ký danh mới:", value=after.nick or "Không có", inline=True)
            await self.send_log(after.guild, embed)

        # B. Hồ sơ máy chủ: Thay đổi Vai trò (Roles) của thành viên
        if before.roles != after.roles:
            added_roles = [role.mention for role in after.roles if role not in before.roles]
            removed_roles = [role.mention for role in before.roles if role not in after.roles]
            if added_roles or removed_roles:
                embed = discord.Embed(title="🧐 Chuyển dịch quyền năng (Roles Member)", color=discord.Color.teal(), timestamp=datetime.datetime.now())
                embed.add_field(name="Mục tiêu tác động:", value=after.mention, inline=False)
                if added_roles:
                    embed.add_field(name="➤ Được ban thêm:", value=", ".join(added_roles), inline=False)
                if removed_roles:
                    embed.add_field(name="➤ Bị tước đoạt mất:", value=", ".join(removed_roles), inline=False)
                await self.send_log(after.guild, embed)

        # C. Thay đổi Ảnh đại diện (An toàn chống crash - Kiểm tra cả Avatar Server và Avatar Chính)
        before_guild_avatar = before.guild_avatar.url if before.guild_avatar else None
        after_guild_avatar = after.guild_avatar.url if after.guild_avatar else None

        before_global_avatar = before.avatar.url if before.avatar else None
        after_global_avatar = after.avatar.url if after.avatar else None

        # Trường hợp 1: Đổi avatar riêng được thiết lập trong Server này
        if before_guild_avatar != after_guild_avatar:
            embed = discord.Embed(title="🖼️ Thay đổi dung mạo máy chủ (Server Avatar)", color=discord.Color.blurple(), timestamp=datetime.datetime.now())
            embed.add_field(name="Cá thể:", value=after.mention, inline=False)
            embed.set_thumbnail(url=before_guild_avatar or before.display_avatar.url)
            embed.set_image(url=after_guild_avatar or after.display_avatar.url)
            await self.send_log(after.guild, embed)
            
        # Trường hợp 2: Đổi avatar CHÍNH của tài khoản gốc trên toàn Discord
        elif before_global_avatar != after_global_avatar:
            embed = discord.Embed(title="🧐 Bản thể thay đổi dung mạo chính a (Global Avatar)", color=discord.Color.purple(), timestamp=datetime.datetime.now())
            embed.add_field(name="Cá thể:", value=after.mention, inline=False)
            embed.add_field(name="ID tài khoản:", value=f"`{after.id}`", inline=False)
            if before_global_avatar: embed.set_thumbnail(url=before_global_avatar)
            if after_global_avatar: embed.set_image(url=after_global_avatar)
            await self.send_log(after.guild, embed)

        # D. Hồ sơ chính: Thay đổi Tên hiển thị toàn cục (Global Display Name)
        if before.global_name != after.global_name:
            embed = discord.Embed(title="✍️ Thay đổi Tên hiển thị chính (Display Name)", color=discord.Color.light_grey(), timestamp=datetime.datetime.now())
            embed.add_field(name="Bản thể:", value=after.mention, inline=False)
            embed.add_field(name="Tên hiển thị cũ:", value=f"`{before.global_name or before.name}`", inline=True)
            embed.add_field(name="Tên hiển thị mới:", value=f"`{after.global_name or after.name}`", inline=True)
            await self.send_log(after.guild, embed)

        # E. Hồ sơ chính: Thay đổi Chân danh gốc tài khoản (Username dùng để kết bạn)
        if before.name != after.name:
            embed = discord.Embed(title="🧐 Kẻ vô tri vừa thay đổi CHÂN DANH gốc (Username)", color=discord.Color.dark_grey(), timestamp=datetime.datetime.now())
            embed.add_field(name="Bản thể gốc:", value=after.mention, inline=False)
            embed.add_field(name="Chân danh cũ:", value=f"`{before.name}`", inline=True)
            embed.add_field(name="Chân danh mới:", value=f"`{after.name}`", inline=True)
            await self.send_log(after.guild, embed)

    # ==========================================
    # 4. SERVER LOGS (Nhật ký biến động cấu trúc)
    # ==========================================
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        embed = discord.Embed(title="🧐 Một không gian mới được kiến tạo (Channel Create)", color=discord.Color.green(), timestamp=datetime.datetime.now())
        embed.add_field(name="Tên không gian:", value=f"{channel.name} ({channel.mention if isinstance(channel, discord.TextChannel) else 'Kênh ẩn/Voice'})", inline=False)
        embed.add_field(name="Phân loại:", value=str(channel.type).upper(), inline=True)
        await self.send_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        embed = discord.Embed(title="🧐 Một không gian vừa bị phá hủy hoàn toàn (Channel Delete)", color=discord.Color.dark_red(), timestamp=datetime.datetime.now())
        embed.add_field(name="Tên không gian cũ:", value=channel.name, inline=True)
        embed.add_field(name="Phân loại cấu trúc:", value=str(channel.type).upper(), inline=True)
        await self.send_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        embed = discord.Embed(title="🧐 Một quyền năng mới được tạo ra (Role Create)", color=discord.Color.from_rgb(46, 204, 113), timestamp=datetime.datetime.now())
        embed.add_field(name="Tên vai trò:", value=role.name, inline=True)
        embed.add_field(name="ID Quyền năng:", value=role.id, inline=True)
        await self.send_log(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        embed = discord.Embed(title="🧐 Một mảnh vỡ quyền năng bị xóa bỏ (Role Delete)", color=discord.Color.from_rgb(192, 41, 43), timestamp=datetime.datetime.now())
        embed.add_field(name="Tên vai trò đã mất:", value=role.name, inline=False)
        await self.send_log(role.guild, embed)

    # ==========================================
    # 5. ADVANCED LOGS (Voice Channels & Reactions)
    # ==========================================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel == after.channel: return # Tránh kích hoạt nhầm khi chỉ tắt/bật mic

        embed = discord.Embed(color=discord.Color.magenta(), timestamp=datetime.datetime.now())
        embed.set_author(name=f"{member.name} di chuyển sóng âm", icon_url=member.display_avatar.url)

        if before.channel is None and after.channel is not None:
            embed.title = "🔊 Kết nối linh hồn vào Voice"
            embed.description = f"{member.mention} đã tiến vào không gian âm thanh **{after.channel.name}**."
            await self.send_log(member.guild, embed)
        elif before.channel is not None and after.channel is None:
            embed.title = "🔇 Ngắt kết nối khỏi Voice"
            embed.description = f"{member.mention} đã rời khỏi không gian âm thanh **{before.channel.name}**."
            await self.send_log(member.guild, embed)
        elif before.channel is not None and after.channel is not None:
            embed.title = "🔀 Dịch chuyển không gian Voice"
            embed.add_field(name="Từ phòng:", value=before.channel.name, inline=True)
            embed.add_field(name="Sang phòng:", value=after.channel.name, inline=True)
            await self.send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member and payload.member.bot: return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        
        embed = discord.Embed(title="🧐 Thả biểu cảm cảm xúc (Reaction Add)", color=discord.Color.light_embed(), timestamp=datetime.datetime.now())
        embed.add_field(name="Kẻ bày tỏ:", value=f"<@{payload.user_id}>", inline=True)
        embed.add_field(name="Biểu cảm:", value=str(payload.emoji), inline=True)
        embed.add_field(name="Tại Tin nhắn ID:", value=f"[{payload.message_id}](https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id})", inline=False)
        await self.send_log(guild, embed)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        
        embed = discord.Embed(title="🫥 Thu hồi biểu cảm cảm xúc (Reaction Remove)", color=discord.Color.dark_embed(), timestamp=datetime.datetime.now())
        embed.add_field(name="Kẻ rút hồi:", value=f"<@{payload.user_id}>", inline=True)
        embed.add_field(name="Biểu cảm cũ:", value=str(payload.emoji), inline=True)
        embed.add_field(name="Tại Tin nhắn ID:", value=f"[{payload.message_id}](https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id})", inline=False)
        await self.send_log(guild, embed)

async def setup(bot):
    await bot.add_cog(Logs(bot))