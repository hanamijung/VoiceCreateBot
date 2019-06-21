import os
import asyncio
import traceback
import discord
import pymongo
from discord.ext import commands
# from discord.ext.commands.cooldowns import BucketType


class voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_connection = os.environ["VCB_DB_CONNECTION_STRING"]
        self.db_database = os.environ["VCB_DATABASE_NAME"] or "voicedb"
        self.admin_ids = (os.environ["ADMIN_USERS"] or "").split(" ")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        conn = pymongo.MongoClient(self.db_connection)
        db = conn[self.db_database]
        guildID = member.guild.id
        guild = db["guild"]
        voiceGuild = guild.find_one({"guildID": guildID})
        if voiceGuild is None:
            print(f"No voice channel found for GuildID: {guildID}")
        else:
            voiceID = voice[0]
            try:
                if after.channel is not None and after.channel.id == voiceID:
                    voiceChannel = db["voiceChannel"]
                    cooldown = voiceChannel.find_one({"userID": member.id})
                    if cooldown is None:
                        pass
                    else:
                        await member.send("Creating channels too quickly you've been put on a 15 second cooldown!")
                        await asyncio.sleep(15)
                    voiceGuild = guild.find_one({"guildID": guildID})
                    userSettings = db["userSettings"]
                    setting = userSettings.find_one({"userID": member.id})
                    guildSettingsCollection = db["guildSettings"]
                    guildSetting = guildSettingsCollection.find_one({"guildID": guildID})
                    # Set default for setting and guildSetting
                    if setting is None:
                        name = f"{member.name}'s channel"
                        if guildSetting is None:
                            limit = 0
                        else:
                            limit = guildSetting[0]
                    else:
                        if guildSetting is None:
                            name = setting[0]
                            limit = setting[1]
                        elif guildSetting is not None and setting[1] == 0:
                            name = setting[0]
                            limit = guildSetting[0]
                        else:
                            name = setting[0]
                            limit = setting[1]
                    categoryID = voice[0]
                    mid = member.id
                    category = self.bot.get_channel(categoryID)
                    print(f"Creating channel {name} in {category}")
                    channel2 = await member.guild.create_voice_channel(name, category=category)
                    channelID = channel2.id
                    print(f"Moving {member} to {channel2}")
                    await member.move_to(channel2)
                    print(f"Setting permissions on {channel2}")
                    await channel2.set_permissions(self.bot.user, connect=True, read_messages=True)
                    print(f"Set user limit to {limit} on {channel2}")
                    await channel2.edit(name=name, user_limit=limit)
                    print(f"Track voiceChannel {mid},{channelID}")
                    voiceChannel.insert_one(
                        {"userID": mid, "voiceID": channelID})

                    def check(a, b, c):
                        return len(channel2.members) == 0
                    await self.bot.wait_for('voice_state_update', check=check)
                    print(f"Deleting Channel {channel2} because everyone left")
                    await channel2.delete()
                    await asyncio.sleep(3)
                    voiceChannel.delete_many({"userID": mid})
            except Exception as ex:
                print(ex)
                traceback.print_exc()

    @voice.command(pass_context=True)
    async def help(self, ctx):
        embed = discord.Embed(title="Help", description="", color=0x7289da)
        embed.set_author(name="Voice Create", url="http://darthminos.tv",
                         icon_url="https://i.imgur.com/EIqP24c.png")
        embed.add_field(name=f'**Commands**', value=f'**Lock your channel by using the following command:**\n\n`.voice lock`\n\n------------\n\n'
                        f'**Unlock your channel by using the following command:**\n\n`.voice unlock`\n\n------------\n\n'
                        f'**Change your channel name by using the following command:**\n\n`.voice name <name>`\n\n**Example:** `.voice name EU 5kd+`\n\n------------\n\n'
                        f'**Change your channel limit by using the following command:**\n\n`.voice limit number`\n\n**Example:** `.voice limit 2`\n\n------------\n\n'
                        f'**Give users permission to join by using the following command:**\n\n`.voice permit @person`\n\n**Example:** `.voice permit @Sam#9452`\n\n------------\n\n'
                        f'**Claim ownership of channel once the owner has left:**\n\n`.voice claim`\n\n**Example:** `.voice claim`\n\n------------\n\n'
                        f'**Remove permission and the user from your channel using the following command:**\n\n`.voice reject @person`\n\n**Example:** `.voice reject @Sam#9452`\n\n', inline='false')
        embed.set_footer(
            text='Bot developed by Sam#9452. Improved by DarthMinos#1161')
        await ctx.channel.send(embed=embed)

    @commands.group()
    async def voice(self, ctx):
        pass

    @voice.command(pass_context=True)
    async def setup(self, ctx):
        conn = pymongo.MongoClient(self.db_connection)
        db = conn[self.db_database]
        guildID = ctx.guild.id
        print(f"User id triggering setup: {ctx.author.id}")
        print(f"Owner id: {ctx.guild.owner.id}")
        print(self.admin_ids)
        print(str(ctx.author.id) in self.admin_ids)
        aid = ctx.author.id
        if ctx.author.id == ctx.guild.owner.id or str(ctx.author.id) in self.admin_ids:
            def check(m):
                return m.author.id == ctx.author.id
            await ctx.channel.send("**You have 60 seconds to answer each question!**")
            await ctx.channel.send(f"**Enter the name of the category you wish to create the channels in:(e.g Voice Channels)**")
            try:
                category = await self.bot.wait_for('message', check=check, timeout=60.0)
            except asyncio.TimeoutError:
                await ctx.channel.send('Took too long to answer!')
            else:
                new_cat = await ctx.guild.create_category_channel(category.content)
                await ctx.channel.send('**Enter the name of the voice channel: (e.g Join To Create)**')
                try:
                    channel = await self.bot.wait_for('message', check=check, timeout=60.0)
                except asyncio.TimeoutError:
                    await ctx.channel.send('Took too long to answer!')
                else:
                    try:
                        channel = await ctx.guild.create_voice_channel(channel.content, category=new_cat)
                        guild = db["guild"]
                        voiceGroup = guild.find_one(
                            {"guildID": guildID, "ownerID": aid})
                        if voiceGroup is None:
                            guild.insert_one(
                                {"guildID": guildID, "ownerID": aid, "voiceChannelID": channel.id, "voiceCategoryID": new_cat.id})
                        else:

                            guild.update_one({"guildID": guildID}, {"$inc": { "guildID": guildID, "ownerID": aid, "voiceChannelID": channel.id, "voiceCategoryID": new_cat.id}}, True)
                        await ctx.channel.send("**You are all setup and ready to go!**")
                    except Exception:
                        traceback.print_exc()
                        await ctx.channel.send("You didn't enter the names properly.\nUse `.voice setup` again!")
        else:
            await ctx.channel.send(f"{ctx.author.mention} only the owner or admins of the server can setup the bot!")

    @commands.command(pass_context=True)
    async def setlimit(self, ctx, num):
        conn = pymongo.MongoClient(self.db_connection)
        db = conn[self.db_database]
        # removed the specific user permission and checked for admin status instead.
        if ctx.author.id == ctx.guild.owner.id or ctx.author.id in self.admin_ids:
            guildSettings = db["guildSettings"]
            voiceGroup = guildSettings.find_one({"guildID": ctx.guild.id})
            if voiceGroup is None:
                guildSettings.insert_one(
                    {"guildID": ctx.guild.id, "channelName": f"{ctx.author.name}'s channel", "channelLimit": num})
            else:
                guildSettings.update_one({"guildID": ctx.guild.id}, { "inc$": {"channelLimit": num}}, True)
            await ctx.send("You have changed the default channel limit for your server!")
        else:
            await ctx.channel.send(f"{ctx.author.mention} only the owner or admins of the server can setup the bot!")

    @setup.error
    async def info_error(self, ctx, error):
        print(error)

    @voice.command()
    async def lock(self, ctx):
        conn = pymongo.MongoClient(self.db_connection)
        db = conn[self.db_database]
        aid = ctx.author.id
        print(f"{ctx.author} triggered lock")
        voiceChannel = db["voiceChannel"]
        voiceGroup = voiceChannel.find_one({"userID": aid})
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            role = discord.utils.get(ctx.guild.roles, name='@everyone')
            channel = self.bot.get_channel(channelID)
            await channel.set_permissions(role, connect=False, read_messages=True)
            await ctx.channel.send(f'{ctx.author.mention} Voice chat locked! 🔒')

    @voice.command()
    async def unlock(self, ctx):
        conn = pymongo.MongoClient(self.db_connection)
        db = conn[self.db_database]
        aid = ctx.author.id
        voiceChannel = db["voiceChannel"]
        voiceGroup = voiceChannel.find_one({"userID", aid})
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            role = discord.utils.get(ctx.guild.roles, name='@everyone')
            channel = self.bot.get_channel(channelID)
            await channel.set_permissions(role, connect=True, read_messages=True)
            await ctx.channel.send(f'{ctx.author.mention} Voice chat unlocked! 🔓')

    @voice.command(aliases=["allow"])
    async def permit(self, ctx, member: discord.Member):
        conn = pymongo.MongoClient(self.db_connection)
        db = conn[self.db_database]
        aid = ctx.author.id
        voiceChannel = db["voiceChannel"]
        voiceGroup = voiceChannel.find_one({"userID": aid})
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            await channel.set_permissions(member, connect=True)
            await ctx.channel.send(f'{ctx.author.mention} You have permitted {member.name} to have access to the channel. ✅')

    @voice.command(aliases=["deny"])
    async def reject(self, ctx, member: discord.Member):
        conn = pymongo.MongoClient(self.db_connection)
        db = conn[self.db_database]
        aid = ctx.author.id
        guildID = ctx.guild.id
        voiceChannel = db["voiceChannel"]
        voiceGroup = voiceChannel.find_one({"userID": aid})
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            for members in channel.members:
                if members.id == member.id:
                    guild = db["guild"]
                    voiceGroup = guild.find_one({"guildID": guildID})
                    channel2 = self.bot.get_channel(voiceGroup[0])
                    await member.move_to(channel2)
            await channel.set_permissions(member, connect=False, read_messages=True)
            await ctx.channel.send(f'{ctx.author.mention} You have rejected {member.name} from accessing the channel. ❌')

    @voice.command()
    async def limit(self, ctx, limit):
        conn = pymongo.MongoClient(self.db_connection)
        db = conn[self.db_database]
        aid = ctx.author.id
        voiceChannel = db["voiceChannel"]
        voiceGroup = voiceChannel.find_one({"userID": aid})
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            await channel.edit(user_limit=limit)
            await ctx.channel.send(f'{ctx.author.mention} You have set the channel limit to be ' + '{}!'.format(limit))
            guild = db["guild"]
            voiceGroup = guild.find_one({"userID": aid})
            userSettings = db["userSettings"]
            if voiceGroup is None:
                userSettings.insert_one(
                    {"userID": aid, "channelName": f"{ctx.author.name}", "channelLimit": limit})
            else:
                userSettings.update_one(
                    {"userID": aid}, {"inc$": {"channelLimit": limit}})

    @voice.command()
    async def name(self, ctx, *, name):
        conn = pymongo.MongoClient(self.db_connection)
        db = conn[self.db_database]
        aid = ctx.author.id
        voiceChannel = db["voiceChannel"]
        voiceGroup = voiceChannel.find_one({"userID": aid})
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            await channel.edit(name=name)
            await ctx.channel.send(f'{ctx.author.mention} You have changed the channel name to ' + '{}!'.format(name))
            userSettings = db["userSettings"]
            voiceGroup = userSettings.find_one({"userID": aid})
            if voiceGroup is None:
                userSettings.insert_one(
                    {"userID": aid, "channelName": name, "channelLimit": 0})
            else:
                userSettings.update_one(
                    {"userID": aid}, {"inc$": {"channelName": name}})

    @voice.command()
    async def claim(self, ctx):
        ownedByThisUser = False
        conn = pymongo.MongoClient(self.db_connection)
        db = conn[self.db_database]
        channel = ctx.author.voice.channel
        if channel is None:
            await ctx.channel.send(f"{ctx.author.mention} you're not in a voice channel.")
        else:
            aid = ctx.author.id
            voiceChannel = db["voiceChannel"]
            voiceGroup = voiceChannel.find_one({"userID": aid})
            if voiceGroup is None:
                await ctx.channel.send(f"{ctx.author.mention} You can't own that channel!")
            else:
                for data in channel.members:
                    if data.id == voiceGroup[0]:
                        owner = ctx.guild.get_member(voiceGroup[0])
                        await ctx.channel.send(f"{ctx.author.mention} This channel is already owned by {owner.mention}!")
                        ownedByThisUser = True
                if not ownedByThisUser:
                    await ctx.channel.send(f"{ctx.author.mention} You are now the owner of the channel!")
                    voiceChannel.update_one({"voiceID": channel.id}, {
                                            "inc$": {"userID": aid}})


def setup(bot):
    bot.add_cog(voice(bot))
