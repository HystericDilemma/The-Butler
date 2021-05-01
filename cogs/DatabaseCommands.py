import aiohttp
import asyncio
# import bitlyshortener
import cv2
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from discord.ext.commands import BucketType
import html2text
import humanize
import imutils
import json
import numpy
import ordinal
import portolan
import random
import requests
from skimage.filters import threshold_local
import tempfile
import tinydb
import uuid

class DatabaseCommands(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
  
  @commands.command()
  async def afk(self, ctx, *, message = None):
    if ctx.author.display_name.startswith("[AFK] "):
      return
    if ctx.message.mentions:
      await ctx.send(f"{self.bot.errorEmoji} You can't ping anything in your status")
    else:
      if not ctx.author.id == 410590963379994639:
        if len(ctx.author.display_name) <= 26:
          await ctx.author.edit(nick = f"[AFK] {ctx.author.display_name}")
        else:
          await ctx.author.edit(nick = f"[AFK] {ctx.author.display_name[:-6]}")
      with open("cogs/afks.json", "r") as file:
        data = json.load(file)
        data[str(ctx.author.id)] = [str(ctx.message.created_at), message]
      with open("cogs/afks.json", "w") as file:
        json.dump(data, file, indent = 2)
      if not message:
        await ctx.send(f"{self.bot.checkmarkEmoji} Set your AFK")
      else:
        await ctx.send(f"{self.bot.checkmarkEmoji} Set your AFK to `{message}`")
  
  @commands.command(aliases = ["camscan"])
  @commands.cooldown(1, 30, BucketType.user) 
  async def scan(self, ctx):
    def order_points(pts):
      rect = numpy.zeros((4, 2), dtype="float32")
      s = pts.sum(axis=1)
      rect[0] = pts[numpy.argmin(s)]
      rect[2] = pts[numpy.argmax(s)]
      diff = numpy.diff(pts, axis=1)
      rect[1] = pts[numpy.argmin(diff)]
      rect[3] = pts[numpy.argmax(diff)]
      return rect

    def four_point_transform(image, pts):
      rect = order_points(pts)
      (tl, tr, br, bl) = rect
      widthA = numpy.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
      widthB = numpy.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
      maxWidth = max(int(widthA), int(widthB))
      heightA = numpy.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
      heightB = numpy.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
      maxHeight = max(int(heightA), int(heightB))
      dst = numpy.array([
          [0, 0],
          [maxWidth - 1, 0],
          [maxWidth - 1, maxHeight - 1],
          [0, maxHeight - 1]], dtype="float32")
      M = cv2.getPerspectiveTransform(rect, dst)
      warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
      return warped

    message = await ctx.send(f"{self.bot.loadingEmoji} Processing...")
    if not ctx.message.attachments:
      await message.edit(content = f"{self.bot.errorEmoji} Try attaching an image")
      return
    response = requests.get(ctx.message.attachments[0].url)
    file = open("image.png", "wb")
    file.write(response.content)
    file.close()
    try:
      image = cv2.imread("image.png")
    except:
      await message.edit(content = f"{self.bot.errorEmoji} Unable to read your attachment, make sure it's an image")
      return
    ratio = image.shape[0] / 500.0
    orig = image.copy()
    image = imutils.resize(image, height = 500)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(gray, 75, 200)
    cnts = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    cnts = sorted(cnts, key = cv2.contourArea, reverse = True)[:5]
    for c in cnts:
      peri = cv2.arcLength(c, True)
      approx = cv2.approxPolyDP(c, 0.02 * peri, True)
      if len(approx) == 4:
        screenCnt = approx
        break
    try:
      cv2.drawContours(image, screenCnt, -1, (0, 255, 0), 2)
    except:
      await message.edit(content = f"{self.bot.errorEmoji} Could not detect four corners")
      return
    warped = four_point_transform(orig, screenCnt.reshape(4, 2) * ratio)
    warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    T = threshold_local(warped, 11, offset = 10, method = "gaussian")
    warped = (warped > T).astype("uint8") * 255
    cv2.imwrite(f"scanned.png", warped)
    await message.delete()
    await ctx.send(content = f"{self.bot.checkmarkEmoji} Scanned", file = discord.File(f"scanned.png"))
  
  @commands.command()
  @commands.cooldown(1, 10, BucketType.user) 
  async def fact(self, ctx):
    await ctx.trigger_typing()
    message = await ctx.send(f"{self.bot.loadingEmoji} Loading...")
    async with aiohttp.ClientSession() as session:
      async with session.get("https://uselessfacts.jsph.pl/random.json?language=en") as reply:
        factDB = await reply.json()
    embed = discord.Embed(title = ":book: A useless fact", description = f"{factDB['text']}", color = 0xe67e22, timestamp = datetime.utcnow())
    embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
    await message.edit(content = None, embed = embed)
  
  @commands.command(aliases = ["f", "race", "r"])
  @commands.cooldown(1, 10, BucketType.user)
  async def fast(self, ctx):
    await ctx.trigger_typing()
    original = await ctx.send(f"{self.bot.loadingEmoji} Loading...")
    choice = random.choice(["math", "word", "find"])

    # math
    if choice == "math":
      operation = random.choice(["×", "/", "+", "-"])
      numbers = []
      answer = 0
      if operation == "×":
        numbers = [random.randint(0, 20), random.randint(0, 20)]
        answer = numbers[0] * numbers[1]
      elif operation == "/":
        denominator = random.randint(1, 20)
        answer = random.randint(1, 20)
        numbers = [denominator * answer, denominator]
      
      elif operation == "+":
        numbers = [random.randint(50, 100), random.randint(50, 100)]
        answer = numbers[0] + numbers[1]
      else:
        numbers = [random.randint(50, 100), random.randint(50, 100)]
        if numbers[0] < numbers[1]:
          numbers[0], numbers[1] = numbers[1], numbers[0]
        answer = numbers[0] - numbers[1]
      
      embed = discord.Embed(title = ":zap: Math Showdown", description = f"First to solve the following wins!\n```py\n{numbers[0]} {operation} {numbers[1]}```", color = 0xe67e22, timestamp = datetime.utcnow())
      embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
      await original.edit(content = None, embed = embed)
      
      def check(message):
        return message.content == str(int(answer)) and message.channel == ctx.channel
      try:
        message = await self.bot.wait_for("message", timeout = 15, check = check)
      except asyncio.TimeoutError:
        await original.edit(content = f"{self.bot.errorEmoji} Event has expired", embed = None)
      else:
        await message.add_reaction(self.bot.checkmarkEmoji)
        await ctx.send(f"{message.author.mention} wins!")
    # word
    elif choice == "word":
      async with aiohttp.ClientSession() as session:
        async with session.get("https://random-word-api.herokuapp.com/word?number=1") as reply:
          wordDB = await reply.json()
      embed = discord.Embed(title = ":zap: Word Showdown", description = f"First to type the following backwards wins!\n```yaml\n{wordDB[0]}```", color = 0xe67e22, timestamp = datetime.utcnow())
      embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
      await original.edit(content = None, embed = embed)
      def check(message):
        return message.content == (wordDB[0])[::-1] and message.channel == ctx.channel
      try:
        message = await self.bot.wait_for("message", timeout = 15, check = check)
      except asyncio.TimeoutError:
        await original.edit(content = f"{self.bot.errorEmoji} Event has expired", embed = None)
      else:
        await message.add_reaction(self.bot.checkmarkEmoji)
        await ctx.send(f"{message.author.mention} wins!")
    
    # find
    else:
      wrong, right = random.choice(self.bot.emojis), random.choice(self.bot.emojis)
      table = [[wrong, wrong, wrong], [wrong, wrong, wrong], [wrong, wrong, wrong]]
      row, column = random.randint(0, 2), random.randint(0, 2)
      table[row][column] = right
      rowPH = ["A", "B", "C"]
      printedTable = "⠀⠀`1`⠀`2`⠀`3`\n"
      for i in range(0, 3):
        printedTable += f"`{rowPH[i]}` "
        for j in range(0, 3):
          printedTable += f"||{table[i][j]}|| "
        printedTable += "\n"
      answer = (rowPH[row] + str(column + 1)).lower()
      embed = discord.Embed(title = ":zap: Bubble Wrap", description = f"First to type the location to {right} wins!\n(ex: `B2` or `2B`)\n\n{printedTable}", color = 0xe67e22, timestamp = datetime.utcnow())
      embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
      await original.edit(content = None, embed = embed)
      def check(message):
        return message.content.lower() in [answer, answer[::-1]] and message.channel == ctx.channel
      try:
        message = await self.bot.wait_for("message", timeout = 15, check = check)
      except asyncio.TimeoutError:
        await original.edit(content = f"{self.bot.errorEmoji} Event has expired", embed = None)
      else:
        await message.add_reaction(self.bot.checkmarkEmoji)
        await ctx.send(f"{message.author.mention} wins!")
  
  @commands.command()
  @commands.cooldown(1, 10, BucketType.user) 
  async def joke(self, ctx):
    await ctx.trigger_typing()
    message = await ctx.send(f"{self.bot.loadingEmoji} Loading...")
    async with aiohttp.ClientSession() as session:
        async with session.get("https://official-joke-api.appspot.com/jokes/random") as reply:
          jokeDB = await reply.json()
    embed = discord.Embed(title = ":book: A joke", description = f"**{jokeDB['setup']}**", color = 0xe67e22, timestamp = datetime.utcnow())
    embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
    await message.edit(content = None, embed = embed)
    embed = discord.Embed(title = ":book: A joke", description = f"**{jokeDB['setup']}**\n{jokeDB['punchline']}", color = 0xe67e22, timestamp = datetime.utcnow())
    embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
    await asyncio.sleep(2)
    await message.edit(content = None, embed = embed)
  
  @commands.command(aliases = ["lb", "top", "^"])
  @commands.cooldown(1, 10, BucketType.user)
  async def leaderboard(self, ctx):
    with open("cogs/points.json", "r") as file:
      data = json.load(file)
      data = dict(sorted(data.items(), key = lambda item: item[1]))
      data = dict(reversed(list(data.items())))
      lb = []
      for i in data:
        noun = "points"
        if data[i] == 1:
          noun = "point"
        if ctx.author.id == int(i):
          lb.append(f"<@{i}> (`{data[i]}` {noun}) :arrow_left::arrow_left::arrow_left:")
        else:
          lb.append(f"<@{i}> (`{data[i]}` {noun})")
      emojis = [":first_place:", ":second_place:", ":third_place:"]
      output = ""
      if len(lb) <= 15:
        for i in lb:
          if lb.index(i) <= 2:
            output += f"\n{emojis[lb.index(i)]} "
          else:
            output += f"\n**{ordinal(lb.index(i) + 1)} **"
          output += lb[lb.index(i)]
      else:
        for i in range(15):
          if i <= 2:
            output += f"\n{emojis[i]} "
          else:
            output += f"\n**{ordinal(i + 1)}** "
          output += lb[i]
    
    embed = discord.Embed(title = ":trophy: Leaderboard", description = f"Top 15 of the `!trivia` command users\n{output}", color = 0xe67e22, timestamp = datetime.utcnow())
    embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
    await ctx.send(embed = embed)

  # @commands.command()
  # @commands.cooldown(1, 10, BucketType.user) 
  # async def mlink(self, ctx):
  #   arr = ["A", "1", "2", "3", "4", "5", "6"]

  #   embed = discord.Embed(title = "Link Meetings", description = "What is your schedule?\nex: 1-6", color = 0xe67e22, timestamp = datetime.utcnow())
  #   embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
  #   embed.set_thumbnail(url = "https://i.imgur.com/2SB21jS.png")
  #   await ctx.send(embed = embed)
  #   def check(message):
  #     response = message.content.replace(" ", "").upper()
  #     return len(response) == 3 and response[1] == "-" and all(item in arr for item in [response.replace("-", "")[0], response.replace("-", "")[1]]) and arr.index(response[0]) < arr.index(response[2])
  #   try:
  #     message = await self.bot.wait_for("message", timeout = 15, check = check)
  #   except asyncio.TimeoutError:
  #     await ctx.send(content = f"{self.bot.errorEmoji} Event has expired", embed = None)
  #   else:
  #     await message.add_reaction(self.bot.checkmarkEmoji)
  #     await ctx.send("Passed")
  
  @commands.command(aliases = ["testmute"])
  @commands.is_owner()
  async def tmute(self, ctx, member: discord.Member, duration = None):
    if self.bot.adminRole in ctx.author.roles or self.bot.moderatorRole in ctx.author.roles:
      if self.bot.adminRole not in member.roles or self.bot.moderatorRole not in member.roles:
        if self.bot.mutedRole in member.roles:
          await ctx.send(f"{self.bot.errorEmoji} They are already muted")
          return
        with open("cogs/mutes.json", "r") as file:
          data = json.load(file)
        if str(member.id) in data:
          await ctx.send(f"{self.bot.errorEmoji} They are already muted")
        else:
          if duration:
            if duration[-1] in ["m", "h"]:
              seconds = 0
              if duration[-1] == "m":
                seconds = int(duration[:-1]) * 60
              elif duration[-1] == "h":
                seconds = int(duration[:-1]) * 3600
              await member.remove_roles(self.bot.vipRole, self.bot.memberRole)
              await member.add_roles(self.bot.mutedRole)
              await ctx.send(f"{self.bot.checkmarkEmoji} Muted for `{duration}`")
              data[str(ctx.author.id)] = seconds
              with open("cogs/mutes.json", "w") as file:
                json.dump(data, file, indent = 2)
              await asyncio.sleep(seconds)
              with open("cogs/mutes.json", "r") as file:
                data = json.load(file)
              del data[str(ctx.author.id)]
              with open("cogs/mutes.json", "w") as file:
                json.dump(data, file, indent = 2)
            else:
              await ctx.send(f"{self.bot.errorEmoji} Invalid duration, use it as such\nex: `13m` or `0.75h`")
              return
          else:
            await member.remove_roles(self.bot.vipRole, self.bot.memberRole)
            await member.add_roles(self.bot.mutedRole)
            data[str(member.id)] = "infiniy"
            with open("cogs/mutes.json", "w") as file:
              json.dump(data, file, indent = 2)
            await ctx.send(f"{self.bot.checkmarkEmoji} Muted")
      else:
        await ctx.send(f"{self.bot.errorEmoji} That person can't be muted")
    else:
      await ctx.send(f"{self.bot.errorEmoji} Missing permissions")

  # mute command
  @commands.command(aliases = ["stfu"])
  async def mute(self, ctx, user: str, mtime = None):
    mutes = {}
    muteDatabase = tinydb.TinyDB("cogs/muteDatabase.json")
    query = tinydb.Query()
    await ctx.trigger_typing()
    if mtime == None:
        mtime = -1

    member = ctx.message.mentions[0]
    vipStat = self.bot.vipRole in member.roles

    if float(mtime) > 0:
      mtime = float(mtime)

    if ((self.bot.adminRole in ctx.message.author.roles) or (self.bot.moderatorRole in ctx.message.author.roles)) and (self.bot.memberRole not in ctx.message.author.roles):
      if muteDatabase.search(query.id == (str(member.id) + " " + str(member.guild.id))) == [] and (not ((self.bot.adminRole in member.roles) or (self.bot.moderatorRole in member.roles) or (self.bot.botRole in member.roles))):
          if mtime > 0:
            if mtime < 1:
              stime = round(mtime * 60)
              sunit = "seconds"                    

              if stime == 1:
                sunit = "second"
              
              embed = discord.Embed(title = ":mute: Muted", description = f"{member.mention} was muted for `{stime}` {sunit}", color = 0x00FF00, timestamp = datetime.utcnow())
              embed.set_footer(text = f"Muted by {ctx.author}", icon_url = ctx.author.avatar_url)
              embed.set_thumbnail(url = member.avatar_url)
              await ctx.send(embed = embed)
            
            if mtime >= 60:
              htime = mtime / 60
              hunit = "hours"

              if htime == 1:
                hunit = "hour"
              
              embed = discord.Embed(title = ":mute: Muted", description = f"{member.mention} was muted for `{htime}` {hunit}", color = 0x00FF00, timestamp = datetime.utcnow())
              embed.set_author(name = self.bot.user.name, icon_url = self.bot.user.avatar_url)
              embed.set_footer(text = f"Muted by {ctx.author}", icon_url = ctx.author.avatar_url)
              embed.set_thumbnail(url = member.avatar_url)
              await ctx.send(embed = embed)
            
            if (mtime >= 1) and (mtime < 60):
              munit = "minutes"
              
              if mtime == 1:
                munit = "minute"
              
              embed = discord.Embed(title = ":mute: Muted", description = f"{member.mention} was muted for `{mtime}` {munit}", color = 0x00FF00, timestamp = datetime.utcnow())
              embed.set_footer(text = f"Muted by {ctx.author}", icon_url = ctx.author.avatar_url)
              embed.set_thumbnail(url = member.avatar_url)
              await ctx.send(embed = embed)
          
          else:
            embed = discord.Embed(title = ":mute: Muted", description = f"{member.mention} was muted for `infinity` (`∞`)", color = 0x00FF00, timestamp = datetime.utcnow())
            embed.set_footer(text = f"Muted by {ctx.author}", icon_url = ctx.author.avatar_url)
            embed.set_thumbnail(url = member.avatar_url)
            await ctx.send(embed = embed)
          
          muteDatabase.insert({"id":(str(member.id) + " " + str(member.guild.id)), "expires":(mtime * 60)})
          await member.add_roles(self.bot.mutedRole)
          await member.remove_roles(self.bot.memberRole)
          if vipStat:
            await member.remove_roles(self.bot.vipRole)

          if mtime > 0:
            await asyncio.sleep(mtime*60)
            
            await member.remove_roles(self.bot.mutedRole)
            await member.add_roles(self.bot.memberRole)
            if vipStat:
              await member.add_roles(self.bot.vipRole)
              
            if muteDatabase.search(query.id == (str(member.id) + " " + str(member.guild.id))) != []:
              embed = discord.Embed(title = ":loud_sound: Unmuted", description = f"{member.mention}'s mute expired", color = 0x00FF00, timestamp = datetime.utcnow())
              embed.set_footer(text = f"Originally muted by {ctx.author}", icon_url = ctx.author.avatar_url)
              embed.set_thumbnail(url = member.avatar_url)
              await ctx.send(embed = embed)
              muteDatabase.remove(query.id == (str(member.id) + " " + str(member.guild.id)))
      
      else:
        if (self.bot.adminRole in member.roles) or (self.bot.moderatorRole in member.roles) or (self.bot.botRole in member.roles):
          await ctx.send(f"{self.bot.errorEmoji} This user cannot be muted")
      
        else:
          await ctx.send(f"{self.bot.errorEmoji} This user is already muted")
    else:
      await ctx.send(f"{self.bot.errorEmoji} Missing permissions")
  
  @commands.command(aliases = ["read"])
  @commands.cooldown(1, 30, BucketType.user)
  async def ocr(self, ctx, engine = 1):
    message = await ctx.send(f"{self.bot.loadingEmoji} Loading... (this will take a bit)")
    if ctx.message.attachments:
      if engine not in [1, 2]:
        await message.edit(content = f"{self.bot.errorEmoji} Invalid engine, choose `1` or `2` (more info at https://ocr.space/ocrapi#ocrengine)")
        return
      filetypes = [".gif", ".jpg", ".pdf", ".png", ".webp"]
      for i in ctx.message.attachments:
        if list(filter(i.filename.lower().endswith, filetypes)) != []:
          if i.size / 1000 <= 1024:
            async def process(url, apiKey, engine, link):
              payload = {"url": url, "apikey": apiKey, "isCreateSearchablePdf": link, "OCREngine": engine}
              async with aiohttp.ClientSession() as session:
                async with session.post("https://api.ocr.space/parse/image", data = payload) as reply:
                  return await reply.json()
            results = await process(i.url, "35c2b7ce5288957", 2, False)
            if results["IsErroredOnProcessing"]:
              await message.edit(content = f"{self.bot.errorEmoji} An error occured\n```yaml\n{results['ErrorMessage'][0]}```")
              return
            if not results["ParsedResults"][0]["ParsedText"]:
              await message.edit(content = f"{self.bot.errorEmoji} No text was found")
              return
            print(len(results["ParsedResults"][0]["ParsedText"]))
            if len(results["ParsedResults"][0]["ParsedText"]) > 1898:
              embed = discord.Embed(title = ":printer: OCR (Text Detection)", description = f"File Name: [`{i.filename}`]({i.url})\nFile Size: `{i.size / 1000}`kb\nOCR Engine: `{engine}`\nProcess: `{int(results['ProcessingTimeInMilliseconds']) / 1000}`ms", color = 0xe67e22, timestamp = datetime.utcnow())
              embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
              with tempfile.TemporaryFile(mode = "w+") as file:
                file.write(results["ParsedResults"][0]["ParsedText"])
                file.seek(0)
                await message.delete()
                embed = discord.Embed(title = ":printer: OCR (Text Detection)", description = f"File Name: [`{i.filename}`]({i.url})\nFile Size: `{i.size / 1000}`kb\nOCR Engine: `{engine}`\nProcess: `{int(results['ProcessingTimeInMilliseconds']) / 1000}`ms", color = 0xe67e22, timestamp = datetime.utcnow())
                embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
                await ctx.send(embed = embed)
                await ctx.send(file = discord.File(file, filename = "response.txt"))
                return
            embed = discord.Embed(title = ":printer: OCR (Text Detection)", description = f"File Name: [`{i.filename}`]({i.url})\nFile Size: `{i.size / 1000}`kb\nOCR Engine: `{engine}`\nProcess: `{int(results['ProcessingTimeInMilliseconds']) / 1000}`ms\n\nDetected Text:\n```yaml\n{results['ParsedResults'][0]['ParsedText']}```", color = 0xe67e22, timestamp = datetime.utcnow())
            embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
            await message.edit(content = None, embed = embed)
          else:
            await message.edit(content = f"{self.bot.errorEmoji} Your file exceeds the `1024` kb limit")
            return
        else:
          await message.edit(content = f"{self.bot.errorEmoji} Inavlid file type a `.gif`, `.jpg`, `.pdf`, `.png`, `.webp`")
          return
    else:
      await message.edit(content = f"{self.bot.errorEmoji} Try attaching something")
  
  # @commands.command(aliases = ["p"])
  # @commands.check(botOwner)
  # @commands.cooldown(1, 5, BucketType.user)
  # async def points(self, ctx, action, member: discord.Member, amount):
  #   if action.lower() == "add":
  #     if int(amount) > 0:
  #       with open("cogs/points.json", "r") as file:
  #           data = json.load(file)
  #           if str(member.id) not in data:
  #             data[str(member.id)] = int(amount)
  #           else:
  #             data[str(member.id)] += int(amount)
  #       with open("cogs/points.json", "w") as file:
  #         json.dump(data, file, indent = 2)
  #       await ctx.send(f"{self.bot.checkmarkEmoji} Added `{amount}` points to {member.mention}!")
  #     else:
  #       await ctx.send(f"{self.bot.errorEmoji} Enter an amount greater than `0`")
  #   elif action.lower() == "remove":
  #     if int(amount) > 0:
  #       with open("cogs/points.json", "r") as file:
  #         data = json.load(file)
  #         if str(member.id) in data:
  #           if data[str(member.id)] > 0:
  #             data[str(member.id)] -= int(amount)
  #           else:
  #             data[str(member.id)] = 0
  #       with open("cogs/points.json", "w") as file:
  #         json.dump(data, file, indent = 2)
  #       await ctx.send(f"{self.bot.checkmarkEmoji} Removed `{amount}` points from {member.mention}!")
  #     else:
  #       await ctx.send(f"{self.bot.errorEmoji} Enter an amount greater than `0`")
  #   else:
  #     await ctx.send(f"{self.bot.errorEmoji} Invalid argument")
  
  @commands.command(aliases = ["roast", "insultme", "insult"])
  @commands.cooldown(1, 10, BucketType.user)
  async def roastme(self, ctx):
    await ctx.trigger_typing()
    message = await ctx.send(f"{self.bot.loadingEmoji} Loading...")
    async with aiohttp.ClientSession() as session:
        async with session.get("https://evilinsult.com/generate_insult.php?lang=en&type=json") as reply:
          roastDB = await reply.json()
    embed = discord.Embed(title = ":pensive: An insult", description = roastDB["insult"], color = 0xe67e22, timestamp = datetime.utcnow())
    embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
    await message.edit(content = None, embed = embed)
  
  # @commands.command()
  # @commands.cooldown(1, 5, BucketType.user) 
  # async def shorten(self, ctx, *, URL: str):
  #   await ctx.trigger_typing()
  #   message = await ctx.send(f"{self.bot.loadingEmoji} Shortening URL...")
  #   tokensPool = "a9c21c045c5d62380a54a7d3a22b06d8e6396c1c"
  #   shortener = bitlyshortener.Shortener(token = tokensPool, max_cache = 256)
  #   URLs = [URL]
  #   shortenedURL = shortener.shorten_urls(URLs)
  #   print(shortenedURL)
  #   embed = discord.Embed(title = ":link: Shortened Link", description = shortenedURL[0], color = 0xe67e22, timestamp = datetime.utcnow())
  #   embed.set_footer(text = f"Requested by {ctx.author}", icon_url = self.bot.user.avatar_url)
  #   embed.set_thumbnail(url = "https://i.imgur.com/YmjXC7s.png")
  #   await message.edit(content = None, embed = embed)
  
  @commands.command()
  @commands.cooldown(1, 20, BucketType.user) 
  async def grades(self, ctx, username, password):
    await ctx.trigger_typing()
    message = await ctx.send(f"{self.bot.loadingEmoji} Loading...")
    if ctx.message.guild:
      await ctx.message.delete()
      embed = discord.Embed(title = ":scroll: Grades", description = f"You cannot use this command here, please go [here](https://discord.com/channels/@me/704582015667798146) and try again", color = 0xe67e22, timestamp = datetime.utcnow())
      embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
      await message.edit(content = None, embed = embed)
      ctx.command.reset_cooldown(ctx)
      return
    async with aiohttp.ClientSession(auth = aiohttp.BasicAuth(username, password)) as session:
      async with session.get(f"https://dvhs.schoolloop.com/mapi/login?version=3&devToken={uuid.uuid4()}&devOS=iPhone9,4&year={datetime.now().year}") as reply:
        if reply.status != 200:
          if "user" in await reply.text():
            await message.edit(content = f"{self.bot.errorEmoji} Username not found")
          else:
            await message.edit(content = f"{self.bot.errorEmoji} Incorrect password")
          return
        studentDB = await reply.json(content_type = None)
      async with session.get(f"https://dvhs.schoolloop.com/mapi/report_card?studentID={studentDB['userID']}") as reply:
        resultDB = await reply.json(content_type = None)
    
    period = ""
    lastUpdated = ""
    embed = discord.Embed(title = ":scroll: Grades", description = "Your grades/credentials are never saved", color = 0xe67e22, timestamp = datetime.utcnow())
    embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
    for i in resultDB:
      if i["courseName"] != "Access":
        period = "A" if i["period"] == "0" else i["period"]
        lastUpdated = "null" if i["lastUpdated"] == "null" else humanize.naturaltime(datetime.now() - datetime.strptime(i["lastUpdated"], "%m/%d/%y %I:%M %p"))
        embed.add_field(name = f"{period} :small_orange_diamond: {i['courseName']}", value = f"Teacher: `{i['teacherName']}`\nGrade: `{i['grade']}` (`{i['score']}`)\nLast Updated: `{lastUpdated}`", inline = False)
    await message.edit(content = None, embed = embed)
  
  @commands.command(aliases = ["q", "question", "quiz", "t"])
  @commands.cooldown(1, 20, BucketType.user)
  async def trivia(self, ctx, difficulty: str = None):
    await ctx.trigger_typing()
    if ctx.channel.id == 612059384721440791:
      await ctx.send(f"{self.bot.errorEmoji} Any channel but here lmao")
      # trivia.reset_cooldown(ctx)
      ctx.command.reset_cooldown(ctx)
      return

    message = await ctx.send(f"{self.bot.loadingEmoji} Loading...")
    if difficulty:
      if difficulty.startswith("e"):
        difficulty = "easy"
      elif difficulty.startswith("m"):
        difficulty = "medium"
      elif difficulty.startswith("h"):
        difficulty = "hard"
      else:
        await message.edit(content = f"{self.bot.errorEmoji} You can only choose an `easy`, `medium`, or `hard` question")
        # trivia.reset_cooldown(ctx)
        ctx.command.reset_cooldown(ctx)
        return
    else:
      difficulty = random.choice(["easy", "medium", "hard"])
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://opentdb.com/api.php?amount=1&difficulty={difficulty}&type=multiple") as reply:
          triviaDB = await reply.json()

    category = html2text.html2text(triviaDB["results"][0]["category"]).replace("\n", "")
    question = html2text.html2text(triviaDB["results"][0]["question"]).replace("\n", "")    
    choices = [html2text.html2text(triviaDB["results"][0]["correct_answer"]).replace("\n", ""), 
    html2text.html2text(triviaDB["results"][0]["incorrect_answers"][0]).replace("\n", ""), 
    html2text.html2text(triviaDB["results"][0]["incorrect_answers"][1]).replace("\n", ""), 
    html2text.html2text(triviaDB["results"][0]["incorrect_answers"][2]).replace("\n", "")]
    random.shuffle(choices)
    correctIndex = choices.index(html2text.html2text(triviaDB["results"][0]["correct_answer"]).replace("\n", ""))
    reactionsList = ["🇦", "🇧", "🇨", "🇩"]

    embed = discord.Embed(title = "<a:lightbulb:819465502320623657> Trivia", description = f"**Category**: {category}\n**Difficulty**: {difficulty.capitalize()}\n**Question**: {question}\n\n{reactionsList[0]} {choices[0]}\n{reactionsList[1]} {choices[1]}\n{reactionsList[2]} {choices[2]}\n{reactionsList[3]} {choices[3]}\n\nreact with your answer within `10` seconds", color = 0xe67e22, timestamp = datetime.utcnow())
    embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
    await message.edit(content = None, embed = embed)
    
    for i in reactionsList:
      await message.add_reaction(i)

    def check(reaction, user):
      return user == ctx.author and str(reaction.emoji) in reactionsList
    
    try:
      reaction, user = await self.bot.wait_for("reaction_add", timeout = 10, check = check)
    
    # did not respond in time
    except asyncio.TimeoutError:
      await message.clear_reactions()
      # points system
      diffPoints = {"easy": 1, "medium": 2, "hard": 3}
      with open("cogs/points.json", "r") as file:
        data = json.load(file)
        if str(ctx.author.id) in data:
          if data[str(ctx.author.id)] > diffPoints[difficulty]:
            data[str(ctx.author.id)] -= 1
          else:
            data[str(ctx.author.id)] = 0
      with open("cogs/points.json", "w") as file:
        json.dump(data, file, indent = 2)
      
      reactionsList[correctIndex] = self.bot.checkmarkEmoji
      embed = discord.Embed(title = f":alarm_clock: Expired! (-{diffPoints[difficulty]} points)", description = f"**Category**: {category}\n**Difficulty**: {difficulty.capitalize()}\n**Question**: {question}\n\n{reactionsList[0]} {choices[0]}\n{reactionsList[1]} {choices[1]}\n{reactionsList[2]} {choices[2]}\n{reactionsList[3]} {choices[3]}\n\nview leaderboard with `!top`", color = 0xFF383E, timestamp = datetime.utcnow())
      embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
      await message.edit(content = None, embed = embed)
    
    # responded in time
    else:
      await message.clear_reactions()
      
      # correct answer
      if reactionsList.index(str(reaction.emoji)) == correctIndex:
        # points system
        diffPoints = {"easy": 1, "medium": 2, "hard": 3}
        with open("cogs/points.json", "r") as file:
          data = json.load(file)
          if str(ctx.author.id) not in data:
            data[str(ctx.author.id)] = diffPoints[difficulty]
          else:
            data[str(ctx.author.id)] += diffPoints[difficulty]
        with open("cogs/points.json", "w") as file:
          json.dump(data, file, indent = 2)
        
        # embed
        reactionsList[correctIndex] = self.bot.checkmarkEmoji
        embed = discord.Embed(title = f"{self.bot.checkmarkEmoji} Correct! (+{diffPoints[difficulty]} points)", description = f"**Category**: {category}\n**Difficulty**: {difficulty.capitalize()}\n**Question**: {question}\n\n{reactionsList[0]} {choices[0]}\n{reactionsList[1]} {choices[1]}\n{reactionsList[2]} {choices[2]}\n{reactionsList[3]} {choices[3]}\n\nview leaderboard with `!top`", color = 0x3FB97C, timestamp = datetime.utcnow())
        embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
        await message.edit(content = None, embed = embed)
      
      # wrong answer
      else:
        # points system
        diffPoints = {"easy": 1, "medium": 2, "hard": 3}
        with open("cogs/points.json", "r") as file:
          data = json.load(file)
          if str(ctx.author.id) in data:
            if data[str(ctx.author.id)] > diffPoints[difficulty]:
              data[str(ctx.author.id)] -= diffPoints[difficulty]
            else:
              data[str(ctx.author.id)] = 0
        with open("cogs/points.json", "w") as file:
          json.dump(data, file, indent = 2)
        
        # embed
        reactionsList[reactionsList.index(str(reaction.emoji))] = self.bot.errorEmoji
        reactionsList[correctIndex] = self.bot.checkmarkEmoji
        embed = discord.Embed(title = f"{self.bot.errorEmoji} Incorrect! (-{diffPoints[difficulty]} points)", description = f"**Category**: {category}\n**Difficulty**: {difficulty.capitalize()}\n**Question**: {question}\n\n{reactionsList[0]} {choices[0]}\n{reactionsList[1]} {choices[1]}\n{reactionsList[2]} {choices[2]}\n{reactionsList[3]} {choices[3]}\n\nview leaderboard with `!top`", color = 0xFF383E, timestamp = datetime.utcnow())
        embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
        await message.edit(content = None, embed = embed)
  
  # unmute command
  @commands.command(aliases = ["unstfu"])
  async def unmute(self, ctx, user: str):
    mutes = {}
    muteDatabase = tinydb.TinyDB("cogs/muteDatabase.json")
    query = tinydb.Query()
    await ctx.trigger_typing()
    member = ctx.message.mentions[0]
    if (self.bot.adminRole in ctx.message.author.roles) or (self.bot.moderatorRole in ctx.message.author.roles):
      if self.bot.mutedRole in member.roles:
        await member.remove_roles(self.bot.mutedRole)
        if not self.bot.memberRole in member.roles:
          await member.add_roles(self.bot.memberRole)
        embed = discord.Embed(title = ":loud_sound: Unmuted", description = f"{member.mention} was unmuted", color = 0x00FF00, timestamp = datetime.utcnow())
        embed.set_footer(text = f"Unmuted by {ctx.author}", icon_url = ctx.author.avatar_url)
        embed.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = embed)
      
      else:
        embed = discord.Embed(title = f"{self.bot.errorEmoji} Unable to Unmute", description = f"{member.mention} isn't even muted", color = 0xFF0000, timestamp = datetime.utcnow())
        embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
        embed.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = embed)
      
      if not self.bot.memberRole in member.roles:
        await member.add_roles(self.bot.memberRole)
      
      muteDatabase.remove(query.id == (str(member.id) + " " + str(member.guild.id)))
    
    else:
      embed = discord.Embed(title = f"{self.bot.errorEmoji} Missing Permissions", description = f"Required Roles: \n• {self.bot.adminRole.mention} \n• {self.bot.moderatorRole.mention}", color = 0xFF0000, timestamp = datetime.utcnow())   
      embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
      embed.set_thumbnail(url = member.avatar_url)
      await ctx.send(embed = embed)
  
  @commands.command()
  @commands.cooldown(1, 15, BucketType.user) 
  async def weather(self, ctx, *, city = None):
    await ctx.trigger_typing()
    message = await ctx.send(f"{self.bot.loadingEmoji} Loading...")
    
    if not city: city = "San Ramon"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://api.openweathermap.org/data/2.5/weather?appid=e83935ef7ce7823925eeb0bfd2db3f7f&q={city}") as reply:
          weatherDB = await reply.json()
    
    if weatherDB["cod"] == "404":
      await message.edit(content = f"{self.bot.errorEmoji} Invalid city")
      return
    
    sunrise = datetime.fromtimestamp(int(weatherDB["sys"]["sunrise"])) - timedelta(hours = 8)
    sunset = datetime.fromtimestamp(int(weatherDB["sys"]["sunset"])) - timedelta(hours = 8)
    embed = discord.Embed(title = ":partly_sunny: Weather", color = 0xe67e22, timestamp = datetime.utcnow())
    embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
    embed.set_thumbnail(url = f"https://openweathermap.org/img/wn/{weatherDB['weather'][0]['icon']}@4x.png")
    embed.add_field(name = "City", value = f"`{weatherDB['name']}`, `{weatherDB['sys']['country']}`", inline = True)
    embed.add_field(name = "Condition", value = f"`{(weatherDB['weather'][0]['description']).title()}`", inline = True)
    embed.add_field(name = "Cloudiness", value = f"`{weatherDB['clouds']['all']}`%", inline = True)
    embed.add_field(name = "Temperature", value = f"`{round((1.8 * ((weatherDB['main']['temp']) - 273.15)) + 32)}`°F", inline = True)
    embed.add_field(name = "Humidity", value = f"`{weatherDB['main']['humidity']}`%", inline = True)
    embed.add_field(name = "Wind", value = f"`{round((weatherDB['wind']['speed'] * 2.24), 1)}`mph `{portolan.abbr(degree = weatherDB['wind']['deg'])}`", inline = True)
    embed.add_field(name = "Sunrise", value = f"{sunrise.strftime('`%I`:`%M` `%p`')} PST", inline = True)
    embed.add_field(name = "Sunset", value = f"{sunset.strftime('`%I`:`%M` `%p`')} PST", inline = True)
    await message.edit(content = None, embed = embed)
  
  # predict command
  @commands.command(aliases = ["8ball"])
  @commands.cooldown(1, 15, BucketType.user) 
  async def predict(self, ctx, *, question: str):
    await ctx.trigger_typing()
    message = await ctx.send(f"{self.bot.loadingEmoji} Loading...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://8ball.delegator.com/magic/JSON/{question}") as reply:
          predictDB = await reply.json()
    embed = discord.Embed(title = ":8ball: The Mighty 8Ball", color = 0xe67e22, timestamp = datetime.utcnow())
    embed.add_field(name = "Question", value = question, inline = False)
    embed.add_field(name = "Response", value = predictDB["magic"]["answer"], inline = False)
    embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
    embed.set_thumbnail(url = "https://i.imgur.com/LkSBSuR.gif")
    await message.edit(content = None, embed = embed)
  
  # # upload commands
  # @commands.command()
  # @commands.cooldown(1, 15, BucketType.user) 
  # async def upload(self, ctx):
  #   message = await ctx.send(f"{self.bot.loadingEmoji} Loading... (this will take a bit)")
  #   if ctx.message.attachments:
  #     for i in ctx.message.attachments:
  #       # 71cc188d6f0ff7d6ba026bccb2a9b585

  #       embed = discord.Embed(title = ":desktop: Uploaded File", description = "", color = 0xe67e22, timestamp = datetime.utcnow())
  #       embed.set_footer(text = f"Requested by {ctx.author}", icon_url = ctx.author.avatar_url)
  #       await message.edit(content = None, embed = embed)
  #   else:
  #     await message.edit(content = f"{self.bot.errorEmoji} Try attaching something")

def setup(bot):
  bot.add_cog(DatabaseCommands(bot))