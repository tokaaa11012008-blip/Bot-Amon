import discord
from discord.ext import commands
import asyncio
import os
import asyncpg
import random
import psycopg2
from psycopg2.extras import RealDictCursor

# 1. BẬT ĐỦ INTENTS: Bắt buộc phải có reactions để xử lý Reaction Role
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.presences = True 
intents.guilds = True

# Hàm tự động lấy prefix từ PostgreSQL cho từng Server (Guild)
async def get_prefix(bot, message):
    if not message.guild:
        return "!"
    try:
        async with bot.db.acquire() as conn:
            prefix = await conn.fetchval('SELECT prefix FROM server_config WHERE guild_id = $1', str(message.guild.id))
        return prefix if prefix else "!"
    except:
        return "!"

bot = commands.Bot(command_prefix=get_prefix, intents=intents)

# SỬA LỖI: Xóa lệnh help mặc định của hệ thống trước khi nạp cogs/help.py
bot.remove_command("help")

# Khởi tạo cấu trúc các bảng dữ liệu Postgres và tự động vá cột nếu thiếu
async def create_tables():
    async with bot.db.acquire() as conn:
        # Khởi tạo cấu trúc cơ bản cho các bảng (nếu chưa tồn tại)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS server_config (
                guild_id TEXT PRIMARY KEY,
                log_channel_id BIGINT,
                warn_channel_id BIGINT,
                level_channel_id BIGINT,
                prefix TEXT DEFAULT '!'
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_warns (
                guild_id TEXT,
                user_id TEXT,
                warn_count INT DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );
        ''')
        
        # Bảng mới lưu thông tin dữ liệu gán Reaction Role
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS reaction_roles (
                guild_id TEXT,
                message_id TEXT,
                emoji TEXT,
                role_id BIGINT,
                PRIMARY KEY (message_id, emoji)
            );
        ''')
        
        # Tự động vá cấu trúc cột cũ nếu cơ sở dữ liệu đã tồn tại từ trước
        await conn.execute('ALTER TABLE server_config ADD COLUMN IF NOT EXISTS log_channel_id BIGINT;')
        await conn.execute('ALTER TABLE server_config ADD COLUMN IF NOT EXISTS warn_channel_id BIGINT;')
        await conn.execute('ALTER TABLE server_config ADD COLUMN IF NOT EXISTS level_channel_id BIGINT;')
        await conn.execute('ALTER TABLE server_config ADD COLUMN IF NOT EXISTS prefix TEXT DEFAULT \'!\';')
        
        print("🗄️ Database: Khởi tạo dữ liệu và vá cấu trúc tất cả các bảng thành công!")

@bot.event
async def on_ready():
    print(f'🤖 Bot Amon đã trực tuyến thành công: {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Hệ thống: Đã ép buộc đồng bộ {len(synced)} lệnh gạch chéo lên Discord.")
    except Exception as e:
        print(f"❌ Lỗi đồng bộ lệnh Slash: {e}")

# LẮNG NGHE TIN NHẮN: Bắt buộc có để xử lý lệnh gõ bằng Prefix dạng Văn bản
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

async def load_extensions():
    # Quét thư mục cogs để nạp các tính năng tự động
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"✅ Đã tải thành công file: {filename}")
            except Exception as e:
                print(f"❌ Thất bại khi nạp file {filename}. Chi tiết lỗi: {e}")

async def main():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ Lỗi nghiêm trọng: Không tìm thấy biến môi trường DATABASE_URL!")
        return

    bot.db = await asyncpg.create_pool(DATABASE_URL)
    await create_tables()
    await load_extensions()
    await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())