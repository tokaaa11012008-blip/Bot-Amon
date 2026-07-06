import discord
from discord.ext import commands
import datetime

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def log_action(self, guild: discord.Guild, embed: discord.Embed):
        try:
            async with self.bot.db.acquire() as conn:
                log_channel_id = await conn.fetchval('SELECT log_channel_id FROM server_config WHERE guild_id = $1', str(guild.id))
            if log_channel_id:
                channel = self.bot.get_channel(log_channel_id)
                if channel: await channel.send(embed=embed)
        except Exception as e:
            print(f"Lỗi gửi dữ liệu log: {e}")

    @commands.hybrid_command(name="amonkick", description="Loại bỏ con trùng vô dụng.")
    @commands.has_permissions(kick_members=True)
    async def amonkick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Không có lý do"):
        if member.id == ctx.author.id:
            await ctx.send("Ngươi muốn trục xuất ta hay chính ngươi đây, hahaha !", delete_after=5)
            return
        try:
            await member.kick(reason=reason)
            await ctx.send(f" 🧐 con trùng  **{member.name}** đã bị loại bỏ.")

            embed = discord.Embed(title="🐛 Trùng bị loại bỏ ", color=discord.Color.orange(), timestamp=datetime.datetime.now())
            embed.add_field(name="Trùng bị loại bỏ:", value=f"{member.mention} ({member.id})", inline=False)
            embed.add_field(name="Kẻ loại bỏ:", value=ctx.author.mention, inline=False)
            embed.add_field(name="Nguyên nhân loại bỏ:", value=reason, inline=False)
            await self.log_action(ctx.guild, embed)
        except discord.Forbidden:
            await ctx.send("🧐 Ngươi không thể 'Đấm' bản thể danh sách cao hơn a.")
        except Exception as e:
            await ctx.send(f"❌ Bot đã bị ảnh hưởng bởi quyền năng của danh sách 1 {e}")

    @commands.hybrid_command(name="amonban", description="Tước bỏ linh trí hoàn toàn của 1 cá thể trùng thời gian.")
    @commands.has_permissions(ban_members=True)
    async def amonban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Không có lý do"):
        if member.id == ctx.author.id:
            await ctx.send("🧐 Ngươi muốn tước bỏ linh trí bản thân mình sao ta e là ngươi không làm được rồi. dù sao thì quyền được chết của ngươi cũng nằm trong tay ta a Hahahaha.", delete_after=5)
            return
        try:
            await member.ban(reason=reason)
            await ctx.send(f"⊗ Đã tước đoạt linh trí của con trùng mang tên **{member.name}** thành công.")

            embed = discord.Embed(title="⊗ Tước đoạt linh tính của Trùng thời gian", color=discord.Color.red(), timestamp=datetime.datetime.now())
            embed.add_field(name="Con Trùng bị xử lý:", value=f"{member.mention} ({member.id})", inline=False)
            embed.add_field(name="Bản thể thực hiện tước đoạt:", value=ctx.author.mention, inline=False)
            embed.add_field(name="Nguyên nhân loại bỏ :", value=reason, inline=False)
            await self.log_action(ctx.guild, embed)
        except discord.Forbidden:
            await ctx.send("𝓐𝓶𝓸𝓷 Tước đoạt thất bại vì Bản thể này có danh sách cao hơn ngươi.")
        except Exception as e:
            await ctx.send(f"❗❗❗Bị ảnh hưởng bởi quyền năng danh sách 1: {e}")

    @commands.hybrid_command(name="amonmute", description="Trộm đi khả năng nhận biết ngôn ngữ (Mute/Timeout) của một con trùng.")
    @commands.has_permissions(moderate_members=True)
    async def amonmute(self, ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str = "Không có lý do"):
        if member.id == ctx.author.id:
            await ctx.send("🧐 Định tự phong ấn chính mình sao?", delete_after=5)
            return
        try:
            duration = datetime.timedelta(minutes=minutes)
            await member.timeout(duration, reason=reason)
            await ctx.send(f"🤫 Đã trộm đi ngôn ngữ của **{member.name}** trong {minutes} phút.")

            embed = discord.Embed(title="🤫 Trộm mất ngôn ngữ (Timeout)", color=discord.Color.dark_purple(), timestamp=datetime.datetime.now())
            embed.add_field(name="Kẻ bị phong ấn:", value=f"{member.mention} ({member.id})", inline=False)
            embed.add_field(name="Kẻ thực hiện:", value=ctx.author.mention, inline=False)
            embed.add_field(name="Thời gian:", value=f"{minutes} phút", inline=True)
            embed.add_field(name="Lý do:", value=reason, inline=True)
            await self.log_action(ctx.guild, embed)
        except discord.Forbidden:
            await ctx.send("🧐 Quyền năng của ngươi hoặc của ta chưa đủ để chạm tới bản thể danh sách cao hơn.")
        except Exception as e:
            await ctx.send(f"❌ Lỗi dòng thời gian: {e}")
    @commands.hybrid_command(name="amonunmute", description="Trả lại khả năng nhận biết ngôn ngữ (Unmute/Gỡ Timeout) cho một con trùng.")
    @commands.has_permissions(moderate_members=True)
    async def amonunmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Không có lý do"):
        if member.id == ctx.author.id:
            await ctx.send("🧐 Ngươi đang nói bình thường, cần gì phải tự giải phong ấn?", delete_after=5)
            return
            
        # Kiểm tra xem thành viên đó có đang bị timeout hay không
        if not member.is_timed_out():
            await ctx.send(f"🧐 Cá thể **{member.name}** vốn dĩ không bị trộm đi ngôn ngữ.", delete_after=5)
            return

        try:
            # Truyền giá trị None vào timeout để gỡ bỏ hình phạt ngay lập tức
            await member.timeout(None, reason=reason)
            await ctx.send(f"🧐 Đã trả lại khả năng ngôn ngữ cho bản thể **{member.name}**.")

            # Gửi nhật ký (Embed Log) về kênh log hệ thống
            embed = discord.Embed(
                title="🧐 Giải phóng ngôn ngữ (Unmute)", 
                color=discord.Color.green(), 
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="Kẻ được giải thoát:", value=f"{member.mention} ({member.id})", inline=False)
            embed.add_field(name="Kẻ thực hiện ân xá:", value=ctx.author.mention, inline=False)
            embed.add_field(name="Lý do giải phong ấn:", value=reason, inline=False)
            
            await self.log_action(ctx.guild, embed)
            
        except discord.Forbidden:
            await ctx.send("🧐 Ta không thể chạm vào một bản thể thuộc danh sách cao hơn quyền hạn hiện tại.")
        except Exception as e:
            await ctx.send(f"❌ Dòng thời gian bị nhiễu loạn khi giải phong ấn: {e}")
    @commands.hybrid_command(name="warn", description="Cảnh báo con trùng dám phạm luật.")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Không có lý do"):
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        try:
            async with self.bot.db.acquire() as conn:
                await conn.execute('''
                    INSERT INTO user_warns (guild_id, user_id, warn_count)
                    VALUES ($1, $2, 1)
                    ON CONFLICT (guild_id, user_id)
                    DO UPDATE SET warn_count = user_warns.warn_count + 1;
                ''', guild_id, user_id)
                current_warns = await conn.fetchval('SELECT warn_count FROM user_warns WHERE guild_id = $1 AND user_id = $2', guild_id, user_id)
                warn_channel_id = await conn.fetchval('SELECT warn_channel_id FROM server_config WHERE guild_id = $1', guild_id)

            await ctx.send(f"CON TRÙNG {member.name} ĐÃ BỊ CẢNH BÁO.", delete_after=5)

            embed = discord.Embed(title="‹«‹«PHẠM LUẬT NÊN BỊ CÁC BẢN THỂ KHÁC CẢNH CÁO»›»›", description=f"Thời gian chi trùng {member.mention} đã bị các bản thể khác cùng nhau xử lý!", color=discord.Color.yellow(), timestamp=datetime.datetime.now())
            embed.add_field(name="Chủ mưu xử lý :", value=ctx.author.mention, inline=True)
            embed.add_field(name="Số lần bị cảnh cáo :", value=f"**{current_warns}/3**", inline=True)
            embed.add_field(name="Nguyên Nhân:", value=reason, inline=False)

            target_channel = self.bot.get_channel(warn_channel_id) if warn_channel_id else ctx.channel
            if target_channel: await target_channel.send(embed=embed)

            if current_warns >= 3:
                await member.timeout(datetime.timedelta(hours=2), reason="Bị Cảnh cáo 3 lần. Ngươi đã bị trộm mất 1 thứ quan trọng")
                embed_punish = discord.Embed(title="🤫 Hình phạt bổ sung", description=f"{member.mention} đã bị trộm mất khả năng nhân biết ngôn ngữ vì bị trừng phạt 3 lần", color=discord.Color.dark_red())
                if target_channel: await target_channel.send(embed=embed_punish)
                async with self.bot.db.acquire() as conn:
                    await conn.execute('UPDATE user_warns SET warn_count = 0 WHERE guild_id = $1 AND user_id = $2', guild_id, user_id)
        except Exception as e:
            await ctx.send(f"❌ Lỗi: {e}")

    @commands.hybrid_command(name="view_warns", description="Xem số lần bị các bản thế cấp cao hơn cảnh cáo.")
    async def view_warns(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        async with self.bot.db.acquire() as conn:
            count = await conn.fetchval('SELECT warn_count FROM user_warns WHERE guild_id = $1 AND user_id = $2', guild_id, user_id)
        count = count or 0
        await ctx.send(f"🧐 {member.mention} đã bị các bản thể khác trừng phạt **{count}** lần.")

    @commands.hybrid_command(name="clear_warn", description="[Admin] Xóa bỏ toàn bộ số lần bị Cảnh cáo (Warn) của một thời gian chi trùng.")
    @commands.has_permissions(moderate_members=True)
    async def clear_warn(self, ctx: commands.Context, member: discord.Member):
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        try:
            async with self.bot.db.acquire() as conn:
                warn_exists = await conn.fetchval('SELECT warn_count FROM user_warns WHERE guild_id = $1 AND user_id = $2', guild_id, user_id)
                if not warn_exists or warn_exists == 0:
                    await ctx.send(f"🧐 {member.mention} hắn vốn dĩ vô tội a.")
                    return
                await conn.execute('UPDATE user_warns SET warn_count = 0 WHERE guild_id = $1 AND user_id = $2', guild_id, user_id)
                warn_channel_id = await conn.fetchval('SELECT warn_channel_id FROM server_config WHERE guild_id = $1', guild_id)

            await ctx.send(f"𝓐𝓶𝓸𝓷 Đã xá tội cho {member.mention} .")
            embed = discord.Embed(title="🧐 Trùng được ân xá", description=f"Thời gian chi trùng {member.mention} đã được xóa bỏ mọi vết nhơ ", color=discord.Color.green(), timestamp=datetime.datetime.now())
            embed.add_field(name="Bản thể ân xá :", value=ctx.author.mention, inline=True)
            embed.add_field(name="Tình trạng hiện tại:", value="**0 / 3 Cảnh cáo**", inline=True)
            target_channel = self.bot.get_channel(warn_channel_id) if warn_channel_id else ctx.channel
            if target_channel: await target_channel.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Lỗi: {e}")

    @commands.hybrid_command(name="clear", description="Xóa tin nhắn trong kênh.")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int):
        deleted = await ctx.channel.purge(limit=amount + (1 if ctx.interaction is None else 0))
        await ctx.send(f"🧐 𝓐𝓂𝓸𝓃  đã trộm mất {len(deleted)} tin nhắn.", delete_after=5)

async def setup(bot):
    await bot.add_cog(Moderation(bot))