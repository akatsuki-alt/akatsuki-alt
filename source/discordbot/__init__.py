from discordbot.commands.showclears import ShowClearsCommand, ShowServerClearsCommand
from discordbot.commands.show1s import Show1sCommand, ShowServer1sCommand
from discordbot.commands.clanleaderboard import ClanLeaderboardCommand
from discordbot.commands.leaderboard import ShowLeaderboardCommand
from discordbot.commands.show import ShowCommand, ResetCommand
from discordbot.commands.setdefault import SetDefaultCommand
from discordbot.commands.searchmaps import SearchmapsCommand
from discordbot.commands.settings import SettingsCommand
from discordbot.commands.addqueue import AddQueueCommand
from discordbot.commands.servers import ServersCommand
from discordbot.commands.beatmap import BeatmapCommand
from discordbot.commands.recent import RecentCommand
from discordbot.commands.users import UsersCommand
from discordbot.commands.ping import PingCommand
from discordbot.commands.link import LinkCommand
from discordbot.commands.help import HelpCommand

import discordbot.bot as bot

bot.commands.append(PingCommand())
bot.commands.append(ServersCommand())
bot.commands.append(LinkCommand())
bot.commands.append(SetDefaultCommand())
bot.commands.append(ShowCommand())
bot.commands.append(ResetCommand())
bot.commands.append(HelpCommand())
bot.commands.append(RecentCommand())
bot.commands.append(ShowLeaderboardCommand())
bot.commands.append(Show1sCommand())
bot.commands.append(ShowServer1sCommand())
bot.commands.append(ShowClearsCommand())
bot.commands.append(ShowServerClearsCommand())
bot.commands.append(AddQueueCommand())
bot.commands.append(UsersCommand())
bot.commands.append(BeatmapCommand())
bot.commands.append(SearchmapsCommand())
bot.commands.append(SettingsCommand())
bot.commands.append(ClanLeaderboardCommand())