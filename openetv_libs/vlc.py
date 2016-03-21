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
from openetv_libs.helpers import open_file


def get_vlc_pid(pidfile, logging):
    f = open(pidfile, 'r')
    pid = int(f.read())
    f.close()
    logging.debug("[getvlcpid] debug: VLC pid = %d" % int(pid))
    return pid

def write_vlc_pid(pidfile, pid):
    with open_file(pidfile, 'w', 'Could not write pidfile {}'.format(pidfile)) as f:
        f.write(str(pid))


def remove_vlc_pid(pidfile):
    os.remove(pidfile)
