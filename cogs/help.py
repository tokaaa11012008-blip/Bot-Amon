import discord
from discord.ext import commands
import datetime

class HelpCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Xem danh sách toàn bộ các lệnh hỗ trợ của bot Amon.")
    async def help_command(self, ctx: commands.Context):
        embed = discord.Embed(
            title="📚 TRUNG TÂM TRỢ GIÚP & HƯỚNG DẪN",
            description="Dưới đây là danh sách toàn bộ các lệnh bạn có thể sử dụng (Hỗ trợ cả dấu `/` và Prefix văn bản):",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        if self.bot.user.avatar: embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        # Lấy sạch tất cả commands có trong hệ thống bot bao gồm cả Hybrid
        for cmd in self.bot.commands:
            if cmd.name == "help": continue
            embed.add_field(
                name=f"/{cmd.name} hoặc {ctx.prefix}{cmd.name}",
                value=f"└ {cmd.description or 'Không có mô tả chi tiết.'}",
                inline=False
            )
        embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCommand(bot))