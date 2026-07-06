import discord
from discord.ext import commands
from discord import app_commands

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="setup_reaction", description="Thiết lập Reaction Role bằng cách theo dõi cảm xúc tin nhắn.")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        message_id="ID của tin nhắn muốn người dùng thả biểu cảm",
        emoji="Biểu cảm/Emoji dùng để bấm (Ví dụ: ✅)",
        role="Vai trò/Role sẽ nhận được khi bấm vào"
    )
    async def setup_reaction(self, ctx: commands.Context, message_id: str, emoji: str, role: discord.Role):
        try:
            # Ghi đè hoặc thêm mới dữ liệu vào database PostgreSQL
            async with self.bot.db.acquire() as conn:
                await conn.execute('''
                    INSERT INTO reaction_roles (guild_id, message_id, emoji, role_id)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (message_id, emoji)
                    DO UPDATE SET role_id = EXCLUDED.role_id;
                ''', str(ctx.guild.id), message_id, emoji, role.id)
            
            # Thử tìm tin nhắn để bot tự thả cảm xúc mồi
            try:
                msg = await ctx.channel.fetch_message(int(message_id))
                await msg.add_reaction(emoji)
            except:
                pass # Bỏ qua nếu tin nhắn ở kênh khác kênh hiện tại

            await ctx.send(f"✅ Thiết lập thành công! Thành viên thả cảm xúc {emoji} tại tin nhắn `{message_id}` sẽ được gán vai trò {role.mention}.")
        except Exception as e:
            await ctx.send(f"❌ Có lỗi xảy ra trong quá trình thiết lập dữ liệu: {e}")

    # Lắng nghe khi có người nhấn thả reaction
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member.bot or not payload.guild_id:
            return
        
        async with self.bot.db.acquire() as conn:
            role_id = await conn.fetchval('''
                SELECT role_id FROM reaction_roles 
                WHERE message_id = $1 AND emoji = $2
            ''', str(payload.message_id), str(payload.emoji))
            
        if role_id:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild: return
            role = guild.get_role(role_id)
            if role:
                try:
                    await payload.member.add_roles(role)
                except Exception as e:
                    print(f"❌ Lỗi gán vai trò: {e}. Có thể do vai trò của Bot nằm thấp hơn vai trò này.")

    # Lắng nghe khi có người bỏ chọn reaction
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id:
            return
            
        async with self.bot.db.acquire() as conn:
            role_id = await conn.fetchval('''
                SELECT role_id FROM reaction_roles 
                WHERE message_id = $1 AND emoji = $2
            ''', str(payload.message_id), str(payload.emoji))
            
        if role_id:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild: return
            member = await guild.fetch_member(payload.user_id)
            role = guild.get_role(role_id)
            if role and member and not member.bot:
                try:
                    await member.remove_roles(role)
                except Exception as e:
                    print(f"❌ Lỗi gỡ vai trò: {e}.")

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))