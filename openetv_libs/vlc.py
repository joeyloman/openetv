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


def get_vlc_pid(pidfile, logging):
    try:
        with open(pidfile, 'r') as f:
            pid = int(f.read())
            logging.debug("[getvlcpid] debug: VLC pid = %d" % int(pid))
            return pid
    except:
        return None


def write_vlc_pid(pidfile, pid):
    f = open(pidfile, 'w')
    f.write("%d" % pid)
    f.close()


def remove_vlc_pid(pidfile):
    os.remove(pidfile)
