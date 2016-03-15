#
# OpenETV - Copyright (C) 2014 Joey Loman (joey@openetv.org).
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# See files COPYING.GPL2 and COPYING.GPL3 for License information.
#

from ConfigParser import ConfigParser

def get_config(config_file):
    config_obj = ConfigParser()
    config_obj.read(config_file)
    config = {}

    for section in config_obj.sections():
        for item in config_obj.items(section):
            val = item[1]
            try:
                config[section][item[0]] = val
            except KeyError:
                config[section] = {item[0]: val}

    return config
