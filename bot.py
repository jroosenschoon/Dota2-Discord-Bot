"""Make a Dota2 Discord bot."""

import urllib.request as r
import json
import math
import discord
from discord.ext import commands
from bs4 import BeautifulSoup
import ssl

bot = commands.Bot(command_prefix=".")


@bot.event
async def on_ready():
    """Prepare the bot."""
    global ids
    # with open("users.json", 'w') as f:
    #     pass
    with open("users.json") as f:
        ids = json.load(f)
    print("Bot is running")

@bot.command()
async def current_users(ctx):
    """List the current users I know."""
    global ids
    msg = ""
    for user in ids:
        msg += "\t" + user + "\n"
    await ctx.send("The usernames I know:\n" + msg)

@bot.command()
async def favorite_hero(ctx, *username):
    """List a user's most played hero and the win rate with that hero."""
    global ids

    username = " ".join(username)
    try:
        req = r.Request("https://api.opendota.com/api/players/" + str(ids[username]) + "/heroes", headers={'User-Agent': 'Mozilla/5.0'})
        request = r.urlopen(req)
    except KeyError:
        await wrong_username(ctx)
        return


    data = json.load(request)

    hero_id = 0
    most_games = 0
    win_rate = 0
    for hero in data:
        if hero["games"] > most_games:
            most_games = hero["games"]
            hero_id = hero["hero_id"]
            win_rate = hero["win"] / hero["games"]

    name_req = r.Request("https://api.opendota.com/api/heroes", headers={'User-Agent': 'Mozilla/5.0'})
    name_request = r.urlopen(name_req)
    name_data = json.load(name_request)
    name = ""
    for hero in name_data:
        if int(hero["id"]) == int(hero_id):
            name = hero["localized_name"]
            break

    await ctx.send("{} specializes in {} with a win rate of {:.2f}.".format(username, name, win_rate))

@bot.command()
async def mmr_check_id(ctx, user_id=0):
    """
    Show the mmr of the user with the specified user id.
    """
    global ids
    if user_id != 0:
        req = r.Request("https://api.opendota.com/api/players/" + str(user_id), headers={'User-Agent': 'Mozilla/5.0'})
        request = r.urlopen(req)
        data = json.load(request)

        await ctx.send("User's MMR: {}".format(data["mmr_estimate"]["estimate"]))
    else:
        await ctx.send("Please enter a username or id.")

@bot.command()
async def mmr_check_name(ctx, *username):
    """
    Show the mmr of the user with the specified username. This username must be in my database. If not,
    please add it with my .add command.
    """
    global ids

    username = " ".join(username)

    if username != "":
        try:
            req = r.Request("https://api.opendota.com/api/players/" + str(ids[username]), headers={'User-Agent': 'Mozilla/5.0'})
            request = r.urlopen(req)
            data = json.load(request)

            await ctx.send(username + "'s MMR: {}".format(data["mmr_estimate"]["estimate"]))
        except KeyError:
            await wrong_username(ctx)

    else:
        await ctx.send("Please enter a username.")

@bot.command()
async def add(ctx, user_url, *username):
    """
    Add a new username and their id to my database, so I can refer to them later. Specify the username you will
    use to refer to them, and the URL of their dotabuff profile.
    """
    global ids

    username = " ".join(username)

    id = int(user_url.split("/")[-1])
    ids[username] = id
    with open("users.json", 'w') as f:
        json.dump(ids, f)

    await ctx.send("{} with id {} was successfully added.".format(username, id))

@bot.command()
async def friends_this_week(ctx, *username):
    """Show friends specified user played with this week."""
    global ids

    username = " ".join(username)
    try:
        req = r.Request("https://www.dotabuff.com/players/" + str(ids[username]), headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'})
        request = r.urlopen(req)
    except KeyError:
        await wrong_username(ctx)
        return


    b = BeautifulSoup(request.read(), "html.parser")

    temp = b.find("div", {"data-portable": "show-player-friends-achievements"}).section.article.table.tbody.children
    temp2 = b.find("div", {"data-portable": "show-player-friends-achievements"}).section.article.table.tbody

    if temp2.tr.td.text == "No recent matches with friends":
        last_played = b.find("section", {"class": "player-aliases"}).article.table.tbody.tr.td.next_sibling.text
        await ctx.send("{} has not played with friends this week. The last time they played was {}".format(username, last_played))
    else:
        for child in temp:
            icon_url = child.td.div.a.img['src']
            name = child.td.next_sibling.a.text
            matches = child.td.next_sibling.next_sibling.text
            win_rate = child.td.next_sibling.next_sibling.next_sibling.text

            embed = discord.Embed(title=name,
                                  description="\tMatches: " + matches + "\n\tWin rate: " + win_rate,
                                  color=0x552E12)

            embed.set_image(url=icon_url)

            await ctx.send(embed=embed)

@bot.command()
async def power_of_friendship(ctx, *username):
    """Get win rates with friends of the specified user."""
    global ids

    username = " ".join(username)
    try:
        req = r.Request("https://api.opendota.com/api/players/" + str(ids[username]) + "/peers", headers={'User-Agent': 'Mozilla/5.0'})
        request = r.urlopen(req)
    except KeyError:
        await wrong_username(ctx)
        return

    data = json.load(request)

    msg = ""

    sorted_peers = {}

    for peer in data:
        if peer["account_id"] in ids.values():
            sorted_peers[peer["personaname"]] = {"win_rate": (peer['win'] / peer["games"]) * 100, "win": peer['win'], "games": peer["games"]}


    sorted_peers = {k: v for k, v in sorted(sorted_peers.items(), key= lambda item: item[1]["win_rate"], reverse=True)}

    print(type(sorted_peers))
    print(sorted_peers)

    for peer, info in sorted_peers.items():
        msg += "{} Win rate: {:.1f}% ({}/{})\n".format(peer, info['win_rate'], info['win'], info["games"])
    await ctx.send(msg)

@bot.command()
async def get_time_played(ctx, *username):
    """Get the time played of a user."""
    global ids

    username = " ".join(username)

    try:
        req = r.Request("https://www.dotabuff.com/players/" + str(ids[username]) + "/scenarios", headers={'User-Agent': 'Mozilla/5.0'})
    except KeyError:
        await wrong_username(ctx)
        return

    request = r.urlopen(req)


    b = BeautifulSoup(request.read(), "html.parser")


    time_played = b.find("article", {"class": "r-tabbed-table"}).table.tbody.tr.td.next_sibling.next_sibling.next_sibling.text

    await ctx.send(username +  " has played for " + time_played + ".")

@bot.command()
async def player_summary(ctx, *username):
    """Get summary of player stats."""
    global ids

    username = " ".join(username)

    try:
        req = r.Request("https://api.opendota.com/api/players/" + str(ids[username]), headers={'User-Agent': 'Mozilla/5.0'})
    except KeyError:
        await wrong_username(ctx)
        return

    request = r.urlopen(req)
    data = json.load(request)
    print(data)
    icon_url = data["profile"]["avatarfull"]

    req = r.Request("https://www.dotabuff.com/players/" + str(ids[username]) + "/scenarios", headers={'User-Agent': 'Mozilla/5.0'})
    request = r.urlopen(req)

    b = BeautifulSoup(request.read(), "html.parser")

    matches = b.find("article", {"class": "r-tabbed-table"}).table.tbody.tr.td.next_sibling.text
    win_rate = b.find("article", {"class": "r-tabbed-table"}).table.tbody.tr.td.next_sibling.next_sibling.text

    req = r.Request("https://www.dotabuff.com/players/" + str(ids[username]) + "/scenarios", headers={'User-Agent': 'Mozilla/5.0'})
    request = r.urlopen(req)

    b = BeautifulSoup(request.read(), "html.parser")

    time_played = b.find("article", {"class": "r-tabbed-table"}).table.tbody.tr.td.next_sibling.next_sibling.next_sibling.text

    req = r.Request("https://api.opendota.com/api/players/" + str(ids[username]), headers={'User-Agent': 'Mozilla/5.0'})
    request = r.urlopen(req)
    data = json.load(request)

    mmr = data["mmr_estimate"]["estimate"]

    req = r.Request("https://api.opendota.com/api/players/" + str(ids[username]) + "/heroes", headers={'User-Agent': 'Mozilla/5.0'})
    request = r.urlopen(req)
    data = json.load(request)

    hero_id = 0
    most_games = 0
    hero_win_rate = 0
    for hero in data:
        if hero["games"] > most_games:
            most_games = hero["games"]
            hero_id = hero["hero_id"]
            hero_win_rate = round((hero["win"] / hero["games"]) * 100, 2)

    name_req = r.Request("https://api.opendota.com/api/heroes", headers={'User-Agent': 'Mozilla/5.0'})
    name_request = r.urlopen(name_req)
    name_data = json.load(name_request)
    name = ""
    for hero in name_data:
        if int(hero["id"]) == int(hero_id):
            name = hero["localized_name"]
            break
    try:
        req = r.Request("https://www.dotabuff.com/players/" + str(ids[username]), headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'})
    except KeyError:
        await wrong_username(ctx)
        return


    request = r.urlopen(req)

    b = BeautifulSoup(request.read(), "html.parser")

    friend_msg = ""
    for child in b.find("div", {"data-portable":"show-player-friends-achievements"}).section.article.table.tbody.children:
        friend_name = child.td.next_sibling.a.text
        friend_matches = child.td.next_sibling.next_sibling.text
        friend_win_rate = child.td.next_sibling.next_sibling.next_sibling.text
        friend_msg += "\n\t\t" + friend_name + ": matches played: " + friend_matches + ", win rate: " + friend_win_rate

    embed=discord.Embed(title=username,
                    description="\tMMR: " + str(mmr) + "\n\tMatches: " + matches + "\n\tWin rate: " + win_rate
                                 + "\n\tTime played: " + time_played + "\n\tFavorite hero: " + name +
                                 " (win rate: " + str(hero_win_rate) + "%)" + "\n\tFriends played with this week:" + friend_msg,
                    color=0x552E12)

    embed.set_image(url=icon_url)

    await ctx.send(embed=embed)

@bot.command()
async def hero_impact(ctx, *username):
    """Get summary of player stats."""
    global ids

    username = " ".join(username)

    try:
        req = r.Request("https://www.dotabuff.com/players/" + str(ids[username]) + "/heroes?metric=impact", headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'})
    except KeyError:
        await wrong_username(ctx)
        return

    request = r.urlopen(req)

    b = BeautifulSoup(request.read(), "html.parser")

    high_impact_heros = []
    for row in b.find("table", {"class": "sortable"}).tbody.children:
        kill_count = row.td.next_sibling.next_sibling.next_sibling.text
        assist_count = row.td.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.text
        if int(remove_all_characters(kill_count, ",")) + int(remove_all_characters(assist_count, ",")) > 1550:
            high_impact_heros.append(row)

    msg = "Highest impact heroes with at least combined total of 1550 kills and assists.\n"
    for row in high_impact_heros[:5]:
        kill_count = row.td.next_sibling.next_sibling.next_sibling.text
        death_count = row.td.next_sibling.next_sibling.next_sibling.next_sibling.text
        assist_count = row.td.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.text
        msg += "```{:<25}: KDA: {:<5} Kills: {:<5} Deaths: {:<7} Assists: {}\n```".format(row.td.next_sibling.text[:-10], row.td.next_sibling.next_sibling.text, kill_count, death_count, assist_count)

    await ctx.send(msg)

@bot.command()
async def least_impact(ctx, *username):
    """Get a player worst heroes."""
    global ids

    username = " ".join(username)


    try:
        req = r.Request("https://www.dotabuff.com/players/" + str(ids[username]) + "/heroes?metric=impact", headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'})
    except KeyError:
        await wrong_username(ctx)
        return

    request = r.urlopen(req)

    b = BeautifulSoup(request.read(), "html.parser")

    low_impact_heros = []
    for row in b.find("table", {"class": "sortable"}).tbody.children:
        kill_count = row.td.next_sibling.next_sibling.next_sibling.text
        death_count = row.td.next_sibling.next_sibling.next_sibling.next_sibling.text
        assist_count = row.td.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.text
        if int(remove_all_characters(death_count, ",")) > 150 and int(remove_all_characters(kill_count, ",")) + int(remove_all_characters(assist_count, ",")) > 500:
            low_impact_heros.append(row)

    msg = "Lowest impact heroes with at least combined total of 500 kills and assists and at least 150 deaths.\n"
    low_impact_heros.reverse()
    for row in low_impact_heros[:5]:
        kill_count = row.td.next_sibling.next_sibling.next_sibling.text
        death_count = row.td.next_sibling.next_sibling.next_sibling.next_sibling.text
        assist_count = row.td.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.text
        msg += "```{:<25}: KDA: {:<5} Kills: {:<5} Deaths: {:<7} Assists: {}\n```".format(row.td.next_sibling.text[:-10], row.td.next_sibling.next_sibling.text, kill_count, death_count, assist_count)

    await ctx.send(msg)

@bot.command()
async def show_my_average(ctx, *username):
    """
    Show the averages from the last 20 games (including turbo) in win rate, kills, deaths, assists,
    gold per min, XP per min, last hits, hero damage, hero healing, tower damage.
    """
    global ids

    username = " ".join(username)

    # ?api_key=8333d9e4-a460-46b2-be90-d3f0ede2f82d
    try:
        req = r.Request("https://api.opendota.com/api/players/" + str(ids[username]) + "/recentMatches", headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'})
    except KeyError:
        await wrong_username(ctx)
        return

    request = r.urlopen(req)

    data = request.read()

    max_kills = 0
    max_deaths = 0
    max_assists = 0
    xp_per_min = 0
    gold_per_min = 0
    hero_damage	= 0
    tower_damage = 0
    hero_healing = 0
    last_hits	= 0
    print(data)
    data = json.loads(data)

    stats = {
         "kills": "Kills",
         "assists": "Assists",
         "deaths": "Deaths",
         "gold_per_min": "Gold/Min",
         "xp_per_min": "XP/Min",
         "last_hits": "Last Hits",
         "hero_damage": "Hero Damage",
         "hero_healing": "Hero Healing",
         "tower_damage": "Tower Damage",
         "duration": "Duration"
         }

    msg = ""
    for stat in stats:
        if stat != "duration":
            num, _ = get_stats(stat, data)
        else:
            num, _ = get_stats(stat, data, is_time=True)
        msg += "Average " + stats[stat]  + ": " + str(num) + "\n"

    await ctx.send(msg)
    # kills, _ = get_stats("kills", data)
    # assists, _ = get_stats("assists", data)
    # deaths, _ = get_stats("deaths", data)
    # gold_per_min, _ = get_stats("gold_per_min", data)
    # xp_per_min, _ = get_stats("xp_per_min", data)
    # last_hits, _ = get_stats("last_hits", data)
    # hero_damage, _ = get_stats("hero_damage", data)
    # hero_healing, _ = get_stats("hero_healing", data)
    # tower_damage, _ = get_stats("tower_damage", data)
    # duration, _ = get_stats("duration", data, is_time=True)


def get_stats(stat, data, is_time=False):
    s = 0
    count = 0
    max = 0
    for d in data:
        if d['game_mode'] not in [23, 19]:
            count += 1
            s += int(d[stat])
            if d[stat] > max:
                max = d[stat]
            if count == 8:
                break
    average = math.ceil(s / count)

    if not is_time:
        if max > 999:
            max = str(max)
            max = max[:-3] + "." + str(math.ceil(int(max[-3:])))[0] + "k"

        if average > 999:
            average = str(average)
            average = average[:-3] + "." + str(math.ceil(int(average[-3:])))[0] + "k"
    else:
        max_mins = math.floor(max / 60)
        max_secs = max - max_mins*60
        max = str(max_mins) + ":" + str(max_secs)

        average_mins = math.floor(average / 60)
        average_secs = average - average_mins*60
        average = str(average_mins) + ":" + str(average_secs)


    return average, max




    # GameModes:
    #   - Ranked: 22
    #   - Turbo:  23
    #   - Event:  19


    # https://www.opendota.com/players/45755222



    # TODO: Future function idea: "Lane Role" Fetched from
    # GET /players/{account_id}/counts

@bot.command()
async def show_my_max(ctx, *username):
    """
    Show the maximums from the last 20 games (including turbo) in win rate, kills, deaths, assists,
    gold per min, XP per min, last hits, hero damage, hero healing, tower damage.
    """
    global ids

    username = " ".join(username)
    asession = AsyncHTMLSession()
# , headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    try:
        r = await asession.get("https://www.opendota.com/players/" + str(ids[username]))
    except KeyError:
        await wrong_username(ctx)
        return
    await r.html.arender()  # this call executes the js in the page

    try:
        data = r.html.find("div.sc-hIVACf + div", first=True).html
    except AttributeError:
        try:
            data = r.html.find("div.sc-hIVACf + div", first=True).html
        except AttributeError:
            await ctx.send("I am having technical issues. Please try again soon.")
            return
    b = BeautifulSoup(data, "html.parser")

    msg = "Maximums over past 20 games (including turbo games):\n\tKills: "

    kill_str = str(b.ul.li.next_sibling.next_sibling)
    kill_start = kill_str.index("<p style=\"color: rgb(102, 187, 106);\">") + len("<p style=\"color: rgb(102, 187, 106);\">")
    kill_end = kill_str.index("<", kill_start)
    kill_max_start = kill_str.index("<span>", kill_end) + len("<span>")
    kill_max_end = kill_str.index("<", kill_max_start)
    kill_max = kill_str[kill_max_start:kill_max_end]

    death_str = str(b.ul.li.next_sibling.next_sibling.next_sibling)
    death_start = death_str.index("<p style=\"color: rgb(255, 76, 76);\">") + len("<p style=\"color: rgb(255, 76, 76);\">")
    death_end = death_str.index("<", death_start)
    death_max_start = death_str.index("<span>", death_end) + len("<span>")
    death_max_end = death_str.index("<", death_max_start)
    death_max = death_str[death_max_start:death_max_end]

    assists_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling)
    assists_start = assists_str.index("<p style=\"color: rgba(255, 255, 255, 0.6);\">") + len("<p style=\"color: rgba(255, 255, 255, 0.6);\">")
    assists_end = assists_str.index("<", assists_start)
    assists_max_start = assists_str.index("<span>", assists_end) + len("<span>")
    assists_max_end = assists_str.index("<", assists_max_start)
    assists_max = assists_str[assists_max_start:assists_max_end]

    gold_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling)
    gold_start = gold_str.index("<p style=\"color: rgb(201, 175, 29);\">") + len("<p style=\"color: rgb(201, 175, 29);\">")
    gold_end = gold_str.index("<", gold_start)
    gold_max_start = gold_str.index("<span>", gold_end) + len("<span>")
    gold_max_end = gold_str.index("<", gold_max_start)
    gold_max = gold_str[gold_max_start:gold_max_end]

    xp_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling)
    xp_start = xp_str.index("<p style=\"color: rgba(255, 255, 255, 0.87);\">") + len("<p style=\"color: rgba(255, 255, 255, 0.87);\">")
    xp_end = xp_str.index("<", xp_start)
    xp_max_start = xp_str.index("<span>", xp_end) + len("<span>")
    xp_max_end = xp_str.index("<", xp_max_start)
    xp_max = xp_str[xp_max_start:xp_max_end]

    hits_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling)
    hits_start = hits_str.index("<p style=\"color: rgba(255, 255, 255, 0.87);\">") + len("<p style=\"color: rgba(255, 255, 255, 0.87);\">")
    hits_end = hits_str.index("<", hits_start)
    hits_max_start = hits_str.index("<span>", hits_end) + len("<span>")
    hits_max_end = hits_str.index("<", hits_max_start)
    hits_max = hits_str[hits_max_start:hits_max_end]

    dmg_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling)
    dmg_start = dmg_str.index("<p style=\"color: rgba(255, 255, 255, 0.87);\">") + len("<p style=\"color: rgba(255, 255, 255, 0.87);\">")
    dmg_end = dmg_str.index("<", dmg_start)
    dmg_max_start = dmg_str.index("<span>", dmg_end) + len("<span>")
    dmg_max_end = dmg_str.index("<", dmg_max_start)
    dmg_max = dmg_str[dmg_max_start:dmg_max_end]

    heal_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling)
    heal_start = heal_str.index("<p style=\"color: rgba(255, 255, 255, 0.87);\">") + len("<p style=\"color: rgba(255, 255, 255, 0.87);\">")
    heal_end = heal_str.index("<", heal_start)
    heal_max_start = heal_str.index("<span>", heal_end) + len("<span>")
    heal_max_end = heal_str.index("<", heal_max_start)
    heal_max = heal_str[heal_max_start:heal_max_end]

    tower_dmg_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling)
    tower_dmg_start = tower_dmg_str.index("<p style=\"color: rgba(255, 255, 255, 0.87);\">") + len("<p style=\"color: rgba(255, 255, 255, 0.87);\">")
    tower_dmg_end = tower_dmg_str.index("<", tower_dmg_start)
    tower_dmg_max_start = tower_dmg_str.index("<span>", tower_dmg_end) + len("<span>")
    tower_dmg_max_end = tower_dmg_str.index("<", tower_dmg_max_start)
    tower_dmg_max = tower_dmg_str[tower_dmg_max_start:tower_dmg_max_end]

    duration_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling)
    duration_start = duration_str.index("<p style=\"color: rgba(255, 255, 255, 0.87);\">") + len("<p style=\"color: rgba(255, 255, 255, 0.87);\">")
    duration_end = duration_str.index("<", duration_start)
    duration_max_start = duration_str.index("<span>", duration_end) + len("<span>")
    duration_max_end = duration_str.index("<", duration_max_start)
    duration_max = duration_str[duration_max_start:duration_max_end]

    msg += kill_max + "\n\tDeaths: "
    msg += death_max + "\n\tAssists: "
    msg += assists_max + "\n\tGold/min: "
    msg += gold_max + "\n\tXP/min: "
    msg += xp_max + "\n\tLast hits: "
    msg += hits_max + "\n\tHero damage: "
    msg += dmg_max + "\n\tHero healing: "
    msg += heal_max + "\n\tTower damage: "
    msg += tower_dmg_max + "\n\tDuration: "
    msg += duration_max + "\n"

    await ctx.send(msg)

@bot.command()
async def show_my_heroes(ctx, *username):
    """
    Show the heroes that obtained the maximums from the last 20 games (including turbo) in kills, deaths, assists,
    gold per min, XP per min, last hits, hero damage, hero healing, tower damage.
    """
    global ids

    username = " ".join(username)
    asession = AsyncHTMLSession()
    try:
        r = await asession.get("https://www.opendota.com/players/" + str(ids[username]))
    except KeyError:
        await wrong_username(ctx)
        return

    await r.html.arender()  # this call executes the js in the page

    try:
        data = r.html.find("div.sc-hIVACf + div", first=True).html
    except AttributeError:
        try:
            data = r.html.find("div.sc-hIVACf + div", first=True).html
        except AttributeError:
            await ctx.send("I am having technical issues. Please try again soon.")
            return

    b = BeautifulSoup(data, "html.parser")

    msg = "Heroes with maximums over past 20 games (including turbo games):\n\tKills: "

    kill_str = str(b.ul.li.next_sibling.next_sibling)

    kill_img_start = kill_str.index("https://")
    kill_img_end = kill_str.index("?\"", kill_img_start)
    kill_img = kill_str[kill_img_start:kill_img_end]

    a = len("https://steamcdn-a.akamaihd.net/apps/dota2/images/dota_react/heroes/icons/")
    kill_hero = kill_img[a:kill_img.index(".", a)]
    kill_hero = kill_hero.replace("_", " ").title()

    msg += kill_hero + " (" + kill_img + ")\n\tDeaths: "

    death_str = str(b.ul.li.next_sibling.next_sibling.next_sibling)
    death_img_start = death_str.index("https://")
    death_img_end = death_str.index("?\"", death_img_start)
    death_img = death_str[death_img_start:death_img_end]


    a = len("https://steamcdn-a.akamaihd.net/apps/dota2/images/dota_react/heroes/icons/")
    death_hero = death_img[a:death_img.index(".", a)]
    death_hero = death_hero.replace("_", " ").title()

    msg += death_hero + " (" + death_img + ")\n\tAssists: "

    assists_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling)

    assists_img_start = assists_str.index("https://")
    assists_img_end = assists_str.index("?\"", assists_img_start)
    assists_img = assists_str[assists_img_start:assists_img_end]

    a = len("https://steamcdn-a.akamaihd.net/apps/dota2/images/dota_react/heroes/icons/")
    assists_hero = assists_img[a:assists_img.index(".", a)]
    assists_hero = assists_hero.replace("_", " ").title()

    msg += assists_hero + " (" + assists_img + ")\n\tGold/min: "

    gold_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling)

    gold_img_start = gold_str.index("https://")
    gold_img_end = gold_str.index("?\"", gold_img_start)
    gold_img = gold_str[gold_img_start:gold_img_end]

    a = len("https://steamcdn-a.akamaihd.net/apps/dota2/images/dota_react/heroes/icons/")
    gold_hero = gold_img[a:gold_img.index(".", a)]
    gold_hero = gold_hero.replace("_", " ").title()

    msg += gold_hero + " (" + gold_img + ")\n\tXP/min:"

    xp_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling)

    xp_img_start = xp_str.index("https://")
    xp_img_end = xp_str.index("?\"", xp_img_start)
    xp_img = xp_str[xp_img_start:xp_img_end]

    a = len("https://steamcdn-a.akamaihd.net/apps/dota2/images/dota_react/heroes/icons/")
    xp_hero = xp_img[a:xp_img.index(".", a)]
    xp_hero = xp_hero.replace("_", " ").title()

    msg += xp_hero + " (" + xp_img + ")\n\tLast hits: "

    hits_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling)

    hits_img_start = hits_str.index("https://")
    hits_img_end = hits_str.index("?\"", hits_img_start)
    hits_img = hits_str[hits_img_start:hits_img_end]

    a = len("https://steamcdn-a.akamaihd.net/apps/dota2/images/dota_react/heroes/icons/")
    hits_hero = hits_img[a:hits_img.index(".", a)]
    hits_hero = hits_hero.replace("_", " ").title()

    msg += hits_hero + " (" + hits_img + ")\n\tHero damage: "

    dmg_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling)

    dmg_img_start = dmg_str.index("https://")
    dmg_img_end = dmg_str.index("?\"", dmg_img_start)
    dmg_img = dmg_str[dmg_img_start:dmg_img_end]

    a = len("https://steamcdn-a.akamaihd.net/apps/dota2/images/dota_react/heroes/icons/")
    dmg_hero = dmg_img[a:dmg_img.index(".", a)]
    dmg_hero = dmg_hero.replace("_", " ").title()

    msg += dmg_hero + " (" + dmg_img + ")\n\tHero healing: "

    heal_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling)

    heal_img_start = heal_str.index("https://")
    heal_img_end = heal_str.index("?\"", heal_img_start)
    heal_img = heal_str[heal_img_start:heal_img_end]

    a = len("https://steamcdn-a.akamaihd.net/apps/dota2/images/dota_react/heroes/icons/")
    heal_hero = heal_img[a:heal_img.index(".", a)]
    heal_hero = heal_hero.replace("_", " ").title()

    msg += heal_hero + " (" + heal_img + ")\n\tTower damage: "

    tower_dmg_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling)

    tower_dmg_img_start = tower_dmg_str.index("https://")
    tower_dmg_img_end = tower_dmg_str.index("?\"", tower_dmg_img_start)
    tower_dmg_img = tower_dmg_str[tower_dmg_img_start:tower_dmg_img_end]

    a = len("https://steamcdn-a.akamaihd.net/apps/dota2/images/dota_react/heroes/icons/")
    tower_dmg_hero = tower_dmg_img[a:tower_dmg_img.index(".", a)]
    tower_dmg_hero = tower_dmg_hero.replace("_", " ").title()

    msg += tower_dmg_hero + " (" + tower_dmg_img + ")\n\tDuration: "

    duration_str = str(b.ul.li.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling)

    duration_img_start = duration_str.index("https://")
    duration_img_end = duration_str.index("?\"", duration_img_start)
    duration_img = duration_str[duration_img_start:duration_img_end]

    a = len("https://steamcdn-a.akamaihd.net/apps/dota2/images/dota_react/heroes/icons/")
    duration_hero = duration_img[a:duration_img.index(".", a)]
    duration_hero = duration_hero.replace("_", " ").title()

    msg += duration_hero + " (" + duration_img + ")\n"

    await ctx.send(msg)

async def wrong_username(ctx):
    global ids
    msg = "I do not know this username. The usernames I know are:\n"
    for username in ids:
        msg += "\t" + username + "\n"

    msg += "To add a new user, please see my `add` command.\n"
    msg += "If you need further assistance, with adding a new user, please run `.help add`\n"

    await ctx.send(msg)

def remove_all_characters(word, char_to_remove):
    """Remove."""
    result = ""
    for char in word:
        if char != char_to_remove:
            result += char
    return result

bot.run("DISCORD_TOKEN")
