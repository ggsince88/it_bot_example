import logging
import os

my_path = os.path.abspath(os.path.dirname(__file__))

# This is a minimal configuration to get you started with the Text mode.
# If you want to connect Errbot to chat services, checkout
# the options in the more complete config-template.py from here:
# https://raw.githubusercontent.com/errbotio/errbot/master/errbot/config-template.py

BACKEND = 'Text'  # Errbot will start in text mode (console only mode) and will answer commands from there.

BOT_DATA_DIR = my_path + '/data'
BOT_EXTRA_PLUGIN_DIR = my_path + '/custom_plugins'

BOT_LOG_FILE = my_path + '/errbot.log'
BOT_LOG_LEVEL = logging.DEBUG

BOT_ADMINS = ('@CHANGE_ME', '#testroom/CHANGE_ME')  # !! Don't leave that to "@CHANGE_ME" if you connect your errbot to a chat system !!

IT_SUPPORT = ('@test')
ACCESS_CONTROLS_DEFAULT = {
    'allowusers': BOT_ADMINS
}

