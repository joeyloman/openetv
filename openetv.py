#!/usr/bin/env python
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

import os
import sys
import logging
import argparse

from openetv_libs import helpers
from openetv_libs import app


if __name__ == "__main__":
    # get the configuration
    openetv_config = helpers.get_config('config.ini')
    logfile = openetv_config['openetv']['openetv_logfile']

    if openetv_config['openetv']['debug'] == "true":
        logging.basicConfig(filename=openetv_config['openetv']['openetv_logfile'], level=logging.DEBUG)
    else:
        logging.basicConfig(filename=openetv_config['openetv']['openetv_logfile'], level=logging.INFO)

    # check if the logo image file can be found TODO: don't check for existence, just assume its there and handle it
    if not os.path.isfile(openetv_config['openetv']['openetv_dir'] + "/openetv_images/logo-app.png"):
        print 'error: logo image file not found at "{}/openetv_images/logo-app.png"'.format(
            openetv_config['openetv']['openetv_dir'])
        print "       maybe the openetv_dir variable isn't configured correctly?"
        sys.exit(2)

    # check if the vlc executable exists
    if not os.path.isfile(openetv_config['vlc']['vlc_exe']):
        print 'error: vlc executable not found at "{}"'.format(openetv_config['vlc']['vlc_exe'])
        sys.exit(2)

    openetv = app.App(openetv_config, logging)

    action_dict = {
        'start': openetv.start,
        'stop': openetv.stop,
        'restart': openetv.restart,
    }

    parser = argparse.ArgumentParser(prog='OpenEtv')
    parser.add_argument('action', choices=('start', 'stop', 'restart'))
    args = parser.parse_args()

    try:
        action_dict[args.action]()
    except Exception as err:
        try:
            print err.extra_info
        except AttributeError:
            print "no extra_info!"
        sys.exit(1)
