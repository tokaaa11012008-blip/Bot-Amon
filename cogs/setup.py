import discord
from discord.ext import commands

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="setup_prefix", description="Thay đổi dấu lệnh tiền tố (Prefix) cho server.")
    @commands.has_permissions(administrator=True)
    async def setup_prefix(self, ctx: commands.Context, new_prefix: str):
        if len(new_prefix) > 3:
            await ctx.send("❌ Prefix chỉ được từ 1 đến 3 ký tự!", delete_after=5)
            return

        guild_id = str(ctx.guild.id)
        try:
            async with self.bot.db.acquire() as conn:
                await conn.execute('''
                    INSERT INTO server_config (guild_id, prefix)
                    VALUES ($1, $2)
                    ON CONFLICT (guild_id) 
                    DO UPDATE SET prefix = EXCLUDED.prefix;
                ''', guild_id, new_prefix)
            await ctx.send(f"✅ Đã thay đổi dấu lệnh (Prefix) thành công thành: `{new_prefix}`")
        except Exception as e:
            await ctx.send(f"❌ Lỗi: {e}")

    @commands.hybrid_command(name="setup_log_channel", description="Cài đặt kênh nhận nhật ký (Modlogs).")
    @commands.has_permissions(administrator=True)
    async def setup_log_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        guild_id = str(ctx.guild.id)
        try:
            async with self.bot.db.acquire() as conn:
                await conn.execute('''
                    INSERT INTO server_config (guild_id, log_channel_id)
                    VALUES ($1, $2)
                    ON CONFLICT (guild_id) 
                    DO UPDATE SET log_channel_id = EXCLUDED.log_channel_id;
                ''', guild_id, channel.id)
            await ctx.send(f"✅ Đã thiết lập kênh nhận Logs thành công: {channel.mention}")
        except Exception as e:
            await ctx.send(f"❌ Lỗi: {e}")

    @commands.hybrid_command(name="setup_warn_channel", description="Cài đặt kênh thông báo Warn công khai.")
    @commands.has_permissions(administrator=True)
    async def setup_warn_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        guild_id = str(ctx.guild.id)
        try:
            async with self.bot.db.acquire() as conn:
                await conn.execute('''
                    INSERT INTO server_config (guild_id, warn_channel_id)
                    VALUES ($1, $2)
                    ON CONFLICT (guild_id) 
                    DO UPDATE SET warn_channel_id = EXCLUDED.warn_channel_id;
                ''', guild_id, channel.id)
            await ctx.send(f"✅ Đã thiết lập kênh thông báo Warn thành công: {channel.mention}")
        except Exception as e:
            await ctx.send(f"❌ Lỗi: {e}")


async def setup(bot):
    await bot.add_cog(Setup(bot))