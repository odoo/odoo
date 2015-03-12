# -*- coding: utf-8 -*-

""" Tests for the configuration file/command-line arguments. """

# This test should be run from its directory.

# TODO A configmanager object cannot parse multiple times a config file
# and/or the command line, preventing to 'reload' a configuration.

import os

import config

config_file_00 = os.path.join(os.path.dirname(__file__),'test-config-values-00.conf')

# 1. No config file, no command-line arguments (a.k.a. default values)

conf = config.configmanager()
conf.parse_config()

assert conf['osv_memory_age_limit'] == 1.0
assert os.path.join(conf['root_path'], 'addons') == conf['addons_path']

# 2. No config file, some command-line arguments

conf = config.configmanager()
# mess with the optparse.Option definition to allow an invalid path
conf.casts['addons_path'].action = 'store'
conf.parse_config(['--addons-path=/xyz/dont-exist', '--osv-memory-age-limit=2.3'])

assert conf['osv_memory_age_limit'] == 2.3
assert conf['addons_path'] == '/xyz/dont-exist'

# 3. Config file, no command-line arguments

conf = config.configmanager()
conf.parse_config(['-c', config_file_00])

assert conf['osv_memory_age_limit'] == 3.4

# 4. Config file, and command-line arguments

conf = config.configmanager()
conf.parse_config(['-c', config_file_00, '--osv-memory-age-limit=2.3'])

assert conf['osv_memory_age_limit'] == 2.3
