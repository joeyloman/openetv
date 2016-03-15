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

import socket
import time
import os
import atexit
import sys
import signal

from signal import SIGTERM, SIGKILL

from openetv_libs import webserver, vlc

class App(object):
    """
    Main application class
    """
    def __init__(self, openetv_config, logging):
        self.openetv_config = openetv_config
        self.logging = logging

        self.pidfile = self.openetv_config['openetv']['openetv_pidfile']
        self.vlc_pidfile = self.openetv_config['vlc']['vlc_pidfile']

        self.stdin = os.devnull
        self.stdout = self.openetv_config['openetv']['openetv_logfile']
        self.stderr = self.openetv_config['openetv']['openetv_logfile']

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced 
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """

        self.logging.debug("[App::daemonize] debug: entering function")

        # check if we can write the pidfile
        try:
            f = open(self.pidfile, 'w+')
        except IOError:
            print "error: cannot write the pidfile \"" + self.pidfile + "\""
            sys.exit(2)

        f.close

        # do first fork
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit first parent
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("Error fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)
    
        # decouple from parent environment
        os.chdir("/") 
        os.setsid() 
        os.umask(0) 
    
        # do second fork
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit from second parent
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("Error fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1) 
    
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
    
        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile,'w+').write("%s\n" % pid)
    
    def delpid(self):
        """
        Remove the pidfile
        """

        self.logging.debug("[App::delpid] debug: entering function")

        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """

        self.logging.debug("[App::start] debug: entering function")

        # check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            try:
                pid = int(pf.read().strip())
            except ValueError:
                pid = None
            pf.close()
        except IOError:
            pid = None
    
        if pid:
            message = "pidfile %s already exist..daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)
        
        # start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """

        self.logging.debug("[App::stop] debug: entering function")

        # check if VLC is running and kill it
        pid = vlc.get_vlc_pid(self.vlc_pidfile, self.logging)
        if pid:
            try:
                # shutdown VLC (in some circumstances VLC doesn't shutdown properly. that's why we always send the SIGKILL signal).
                os.kill(pid, signal.SIGKILL)
                remove_vlc_pid(self.vlc_pidfile)
            except:
                # VLC is not running, remove the pidfile
                remove_vlc_pid(self.vlc_pidfile)

        # get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
    
        if not pid:
            message = "pidfile %s does not exist..daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart

        # try killing the daemon process    
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """

        self.logging.debug("[App::restart] debug: entering function")

        self.stop()
        self.start()

    def run(self):
        """
        Run the application
        """

        self.logging.debug("[App::run] debug: entering function")

        # start the OpenETV webservice
        webserver.startservice(self.openetv_config, self.logging)
