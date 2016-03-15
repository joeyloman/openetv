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

from openetv_libs import app, config, vlc
#from openetv_libs.log import log

if __name__ == "__main__":
    # get the configuration
    openetv_config = config.get_config('config.ini')

    # check if the logo image file can be found
    if not os.path.isfile(openetv_config['openetv']['openetv_dir'] + "/openetv_images/logo-app.png"):
        print "error: logo image file not found at \"" + openetv_config['openetv']['openetv_dir'] + "/openetv_images/logo-app.png" + "\""
        print "       maybe the openetv_dir variable isn't configured correctly?"
        sys.exit(2)

    # check if we can write the OpenETV logfile
    try:
        f = open(openetv_config['openetv']['openetv_logfile'],'a')
    except IOError:
        print "error: cannot write to logfile \"" + openetv_config['openetv']['openetv_logfile'] + "\""
        sys.exit(2)

    f.close

    if openetv_config['openetv']['debug'] == "true":
        logging.basicConfig(filename=openetv_config['openetv']['openetv_logfile'], level=logging.DEBUG)
    else:
        logging.basicConfig(filename=openetv_config['openetv']['openetv_logfile'], level=logging.INFO)

    # check if we can write the OpenETV pidfile
    try:
        f = open(openetv_config['openetv']['openetv_pidfile'],'a')
    except IOError:
        print "error: cannot write to pidfile \"" + openetv_config['openetv']['openetv_pidfile'] + "\""
        sys.exit(2)

    f.close

    # check if we can write the VLC pidfile
    try:
        f = open(openetv_config['vlc']['vlc_pidfile'],'a')
    except IOError:
        print "error: cannot write to pidfile \"" + openetv_config['vlc']['vlc_pidfile'] + "\""
        sys.exit(2)

    f.close
    vlc.remove_vlc_pid(openetv_config['vlc']['vlc_pidfile'])

    # check if the vlc executable exists
    if not os.path.isfile(openetv_config['vlc']['vlc_exe']):
        print "error: vlc executable not found at \"" + openetv_config['vlc']['vlc_exe'] + "\""
        sys.exit(2)

    openetv = app.App(openetv_config, logging)
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            logging.info("[Main] OpenETV started.")
            openetv.start()
        elif 'stop' == sys.argv[1]:
            logging.info("[Main] OpenETV stopped.")
            openetv.stop()
        elif 'restart' == sys.argv[1]:
            logging.info("[Main] OpenETV restarted.")
            openetv.restart()
        else:
            print "usage: %s start|stop|restart" % sys.argv[0]
            sys.exit(2)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
