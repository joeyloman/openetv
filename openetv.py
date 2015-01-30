#!/bin/env python
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
import urllib
import urllib2
import subprocess
import time
import datetime
import os
import atexit
import sys
import libxml2
import re
import base64
import signal

from signal import SIGTERM

###################################################################################
### Configuration
###################################################################################

#
# OpenETV options
#
name             = "OpenETV"
version          = "201501301"

#
# Specify the directory where OpenETV is located
#
openetv_dir         = "/opt/openetv"

#
# The following files are saved to the current working directory
#
logo_file        = "logo-app.png"
log_file         = "openetv.log"
pid_file         = "openetv.pid"

#
# The max options below should always be set to a larger value than the channel count in the bouquet list
#
max_bouquets     = 1000
max_channels     = 1000

#
# Debugging:
#
# None = disabled
# 1 = enabled
#
debug            = None

#
# Daemon tcp binding options
#
bind_host        = "0.0.0.0"
bind_port        = 8081

#
# Enigma2 WebIF options
#
# enigma2_host     : hostname or ip adress of the enigma2 host
# enigma2_port     : tcp port where the enigma2 host is listening on
# enigma2_username : if authentication is enabled on the WebIF provide a enigma2 username
# enigma2_password : if authentication is enabled on the WebIF provide a enigma2 password
# enigma2_use_ssl  : set this to yes if https is enabled on the enigma2 host
#
enigma2_host     = "192.168.1.10"
enigma2_port     = 443
enigma2_username = "username"
enigma2_password = "password"
enigma2_use_ssl  = "yes"

#
# VLC options
#

#
# VLC executable path Linux:
#
# Note: cvlc means "command-line VLC"
#
vlc_exe                   = "/usr/bin/cvlc"

#
# VLC executable path Mac OSX:
#
#vlc_exe                   = "/Applications/VLC.app/Contents/MacOS/VLC"

#
# Poor quality:
#
# The following VLC options produce a low quality MPEG1 stream which I used to transcode videos on an old Intel ATOM 330
# and stream it over a 3G network to my cellphone.
#
#vlc_stream_options        = "venc=x264,vcodec=mp1v,vb=160,width=240,height=160,fps=18,acodec=mp3,ab=96,samplerate=44100"

#
# Medium quality:
#
# The following VLC options produce a medium quality MPEG1 stream for Tablets and Smart Phones.
#
#vlc_stream_options        = "venc=x264,vcodec=mp1v,vb=320,width=480,height=384,fps=25,acodec=mp3,ab=128,samplerate=44100"

#
# Good quality:
#
# The following VLC options produce a good quality H264 stream for Tablets and Smart Phones. This one is tested on a
# Intel ATOM C2750. This also streams without problems over a 3G network to my cellphone.
#
vlc_stream_options        = "venc=x264,vcodec=h264,width=720,height=576,fps=25,acodec=mp3,ab=128,samplerate=44100"

#
# VLC stream bindings
#
vlc_http_stream_bind_addr = "0.0.0.0"
vlc_http_stream_bind_port = 8080


###################################################################################
### Functions
###################################################################################

def log(msg):
    ts = time.time()
    timestamp = datetime.datetime.fromtimestamp(ts).strftime('[%Y-%m-%d %H:%M:%S] ')

    f = open(log_file_path, 'a')
    f.write(timestamp + msg + "\n")
    f.close()

def html_header():
    html = "<html>\n"
    html += "<head>\n"
    html += "<title>\n"
    html += name + " version " + version
    html += "</title>\n"
    html += "</head>\n"
    html += "<style>\n"
    html += "body,a { font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: 7e7e7e; line-height: 17px; }\n"
    html += "td { font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: white; line-height: 17px; }\n"
    html += "input,select { font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: black; line-height: 17px; background-color: d7d0d0;}\n"
    html += "tr.even { background-color: #30ba14; color: white;}\n"
    html += "tr.odd { background-color: #60148c; color: white;}\n"
    html += "</style>\n"
    html += "<body>\n"

    f = open(logo_file_path, 'r')
    image_data = f.read()
    f.close()

    html += "<img src=\"data:image/png;base64,"

    # split the base64 image data into chunks (according to the rfc)
    b64 = base64.b64encode(image_data)
    chunksize = 64
    for pos in xrange(0, len(b64), chunksize):
        html += b64[pos:pos+chunksize] + "\n"

    html += "\" /><br><br>\n"

    return html

def html_menu(active_channel,active_channel_name):
    html = "<form>\n"

    html += "<input type=button value='refresh bouquet list' onClick=location.href='/refresh=bouquet'>\n"
    html += "<input type=button value='refresh channel list' onClick=location.href='/refresh=channel'>\n"

    html += "</form>\n"

    if active_channel < max_channels:
        html += "<b>Now Playing: " + active_channel_name + "</b><br><br>\n"
        html += "<b>Stream: http://" + vlc_http_stream_bind_addr + ":%d" % vlc_http_stream_bind_port + "</b><br>\n"

    return html

def html_footer():
    html = "<br><i>" + name + " version " + version + " - <a href=\"http://www.openetv.org\" target=\"_blank\">http://www.openetv.org</a></i><br>\n"
    html += "</body>\n"
    html += "</html>\n"

    return html


###################################################################################
### App class
###################################################################################

class App:
    """
    Main application class
    """
    def __init__(self):
        self.stdin = os.devnull
        self.stdout = log_file_path
        self.stderr = log_file_path
        self.pidfile =  pid_file_path

        self.bouquet_id = 0
        self.bouquet_name = None
        self.bouquet_ref = None

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced 
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """

        if debug:
            log("[App::daemonize] debug: entering function")

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

        if debug:
            log("[App::delpid] debug: entering function")

        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """

        if debug:
            log("[App::start] debug: entering function")

        # Check for a pidfile to see if the daemon already runs
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
        
        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """

        if debug:
            log("[App::stop] debug: entering function")

        # Get the pid from the pidfile
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

        # Try killing the daemon process    
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

        if debug:
            log("[App::restart] debug: entering function")

        self.stop()
        self.start()

    def run(self):
        """
        Run the application
        """

        if debug:
            log("[App::run] debug: entering function")

        r_bouquets = Bouquets()
        r_channels = Channels()

        # refresh bouquet list
        self.rb_res = r_bouquets.refresh_bouquet_list()

        # check if the bouquet list is successfully fetched
        if self.rb_res:
            # get bouquet list
            html_bouquets = r_bouquets.list_bouquets()

            # get bouquet name and ref
            bouquet = r_bouquets.set_active_bouquet(self.bouquet_id)
            self.bouquet_name = bouquet[0]
            self.bouquet_ref = bouquet[1]

        # refresh the channel list
        self.rc_res = r_channels.refresh_channel_list(self.bouquet_name,self.bouquet_ref)

        # socket/bind/listen setup
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((bind_host, bind_port))
        s.listen(5)

        while True:
            c, addr = s.accept()

            if debug:
                log("[App::run] debug: incomming connection from: " + addr[0] + ":%d" % addr[1])

            # recieve HTTP command
            cmd = c.recv(1024).split('\n')[0]

            if debug:
                log("[App::run] debug: command [" + cmd + "]")

            if cmd[:3] == "GET":
                page = cmd.split(' ')[1]

                if debug:
                    log("[App::run] debug: page request [" + page + "]")

                # get current active channels
                active_channel = r_channels.get_active_channel()
                active_channel_name = r_channels.get_active_channel_name()

                if page == "/" or page == "/index.htm" or page == "index.html":
                    """
                    Expected parameters: none
                    """

                    html = html_header()

                    if self.rb_res:
                        html += r_bouquets.list_bouquets()
                    else:
                        html += "<b>Error: could not get bouquet list!</b>"

                    if self.rc_res:
                        html += r_channels.list_channels()

                    html += html_menu(active_channel,active_channel_name)
                    html += html_footer()

                    write_data = "HTTP/1.1 200 OK\n"
                    write_data += "Content-Length: %d\n" % len(html)
                    write_data += "Content-Type: text/html\n\n"
                    write_data += html

                    c.send(write_data)
                elif page[:8] == "/bouquet":
                    """
                    Expected parameters: /bouquet=<bouquet-id>
                    """

                    bid = page.split('=')[1]
                    
                    if debug:
                        log("[App::run] debug: changing bouquet list to [" + bid + "]")

                    try:
                        id = int(bid)
                    except ValueError:
                        html = html_header()

                        if self.rb_res:
                            html += r_bouquets.list_bouquets()
                        else:
                            html += "<b>Error: could not get bouquet list!</b>"

                        html += html_menu(active_channel,active_channel_name)
                        html += "<b>Error: bouquet id is invalid!</b><br>"
                        html += html_footer()

                        write_data = "HTTP/1.1 200 OK\n"
                        write_data += "Content-Length: %d\n" % len(html)
                        write_data += "Content-Type: text/html\n\n"
                        write_data += html

                        c.send(write_data)
                        c.close()

                    if not 0 <= int(bid) < max_bouquets:
                        html = html_header()

                        if self.rb_res:
                            html += r_bouquets.list_bouquets()
                        else:
                            html += "<b>Error: could not get bouquet list!</b>"

                        html += html_menu(active_channel,active_channel_name)
                        html += "<b>Error: bouquetplaylist id is not in range between 0 and 999!</b><br>"
                        html += html_footer()

                        write_data = "HTTP/1.1 200 OK\n"
                        write_data += "Content-Length: %d\n" % len(html)
                        write_data += "Content-Type: text/html\n\n"
                        write_data += html

                        c.send(write_data)
                        c.close()

                    if self.rb_res:
                        # select bouquet
                        self.bouquet_id = id
                        bouquet = r_bouquets.set_active_bouquet(self.bouquet_id)
                        self.bouquet_name = bouquet[0]
                        self.bouquet_ref = bouquet[1]

                    html = html_header()

                    if self.rb_res:
                        html += r_bouquets.list_bouquets()
                    else:
                        html += "<b>Error: could not get bouquet list!</b>"

                    # refresh the channels
                    self.rc_res = r_channels.refresh_channel_list(self.bouquet_name,self.bouquet_ref)
                    if self.rc_res:
                        html += r_channels.list_channels()

                    html += html_menu(active_channel,active_channel_name)
                    html += html_footer()

                    write_data = "HTTP/1.1 200 OK\n"
                    write_data += "Content-Length: %d\n" % len(html)
                    write_data += "Content-Type: text/html\n\n"
                    write_data += html

                    c.send(write_data)
                elif page[:6] == "/start":
                    """
                    Expected parameters: /start=<channel-id>
                    """

                    cid = page.split('=')[1]

                    if debug:
                        log("[App::run] debug: start channel id [" + cid + "]")

                    try:
                        id = int(cid)
                    except ValueError:
                        html = html_header()

                        if self.rb_res:
                            html += r_bouquets.list_bouquets()
                        else:
                            html += "<b>Error: could not get bouquet list!</b>"

                        html += html_menu(active_channel,active_channel_name)
                        html += "<b>Error: playlist id is invalid!</b><br>"
                        html += html_footer()

                        write_data = "HTTP/1.1 200 OK\n"
                        write_data += "Content-Length: %d\n" % len(html)
                        write_data += "Content-Type: text/html\n\n"
                        write_data += html

                        c.send(write_data)
                        c.close()

                    if not 0 <= int(id) < max_channels:
                        html = html_header()

                        if self.rb_res:
                            html += r_bouquets.list_bouquets()
                        else:
                            html += "<b>Error: could not get bouquet list!</b>"

                        html += html_menu(active_channel,active_channel_name)
                        html += "<b>Error: playlist id is not in range between 0 and 999!</b><br>"
                        html += html_footer()

                        write_data = "HTTP/1.1 200 OK\n"
                        write_data += "Content-Length: %d\n" % len(html)
                        write_data += "Content-Type: text/html\n\n"
                        write_data += html

                        c.send(write_data)
                        c.close()

                    html = html_header()

                    if self.rb_res:
                        html += r_bouquets.list_bouquets()
                    else:
                        html += "<b>Error: could not get bouquet list!</b>"

                    # play the selected channel
                    r_channels.play_channel(id)

                    # get current active channels
                    active_channel = r_channels.get_active_channel()
                    active_channel_name = r_channels.get_active_channel_name()

                    if self.rc_res:
                        html += r_channels.list_channels()

                    html += html_menu(active_channel,active_channel_name)
                    html += html_footer()

                    write_data = "HTTP/1.1 200 OK\n"
                    write_data += "Content-Length: %d\n" % len(html)
                    write_data += "Content-Type: text/html\n\n"
                    write_data += html

                    c.send(write_data)

                    # shutdown the socket, otherwise the client still thinks it recieves data
                    c.shutdown(socket.SHUT_RDWR)
                elif page[:5] == "/stop":
                    """
                    Expected parameters: none
                    """

                    if debug:
                        log("[App::run] debug: stop channel id [%d" % active_channel + "]")

                    if active_channel < max_channels:
                        html = html_header()

                        if self.rb_res:
                            html += r_bouquets.list_bouquets()
                        else:
                            html += "<b>Error: could not get bouquet list!</b>"

                        # stop the transcoding process
                        stop_res = r_channels.stop_channel()

                        # get current active channels
                        active_channel = r_channels.get_active_channel()
                        active_channel_name = r_channels.get_active_channel_name()

                        if self.rc_res:
                            html += r_channels.list_channels()

                        html += html_menu(active_channel,active_channel_name)

                        if not stop_res:
                            html += "<b>Error: unable to stop stream, nothing is playing!</b><br>\n"

                        html += html_footer()
                    else:
                        html = html_header()

                        if self.rb_res:
                            html += r_bouquets.list_bouquets()
                        else:
                            html += "<b>Error: could not get bouquet list!</b>"

                        if self.rc_res:
                            html += r_channels.list_channels()

                        html += html_menu(active_channel,active_channel_name)
                        html += html_footer()

                    write_data = "HTTP/1.1 200 OK\n"
                    write_data += "Content-Length: %d\n" % len(html)
                    write_data += "Content-Type: text/html\n\n"
                    write_data += html

                    c.send(write_data)
                elif page[:8] == "/refresh":
                    """
                    Expected parameters: "bouquet" or "channel"
                    """

                    type = page.split('=')[1]

                    html = html_header()

                    # refresh bouquets
                    if type == "bouquet":
                        self.rb_res = r_bouquets.refresh_bouquet_list()

                    if self.rb_res:
                        html += r_bouquets.list_bouquets()

                        # refresh the channel list
                        if type == "channel":
                            self.rc_res = r_channels.refresh_channel_list(self.bouquet_name,self.bouquet_ref)

                        if self.rc_res:
                            html += r_channels.list_channels()
                    else:
                        html += "<b>Error: could not get bouquet list!</b>"

                    html += html_menu(active_channel,active_channel_name)
                    html += html_footer()

                    write_data = "HTTP/1.1 200 OK\n"
                    write_data += "Content-Length: %d\n" % len(html)
                    write_data += "Content-Type: text/html\n\n"
                    write_data += html

                    c.send(write_data)

            if debug:
                log("[App::run] closing connection")

            c.close()


###################################################################################
### Bouquet classes
###################################################################################

class Bouquet:
    def __init__(self, name, ref):
        self.name = name
        self.ref = ref

class Bouquets(object):
    def __init__(self):
        self.bouquets = []

        #
        # Keeps track of the active bouquet
        # 0 = first bouquet
        #
        self.active_bouquet = 0

    def refresh_bouquet_list(self):
        """
        Function which fetches and store the bouquet list

        API url:
          http://<enigma host>/web/getservices

        Return values:
          <?xml version="1.0" encoding="UTF-8"?>
          <e2servicelist>
              <e2service>
                  <e2servicereference>1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet</e2servicereference>
                  <e2servicename>Favourites (TV)</e2servicename>
              </e2service>
          </e2servicelist>
        """

        if debug:
            log("[Bouquets::get_bouquet_list] debug: entering function")

        #from pudb import set_trace; set_trace()
        if enigma2_use_ssl == "yes":
            req_url = "https://" + enigma2_host + ":" + "%d" % enigma2_port + "/web/getservices"
        else:
            req_url = "http://" + enigma2_host + ":" + "%d" % enigma2_port + "/web/getservices"

        if debug:
            log("[Bouquets::get_bouquet_list] debug: opening url: " + req_url)

        req = urllib2.Request(req_url)
        try:
            handle = urllib2.urlopen(req)
        except IOError, e:
            pass
        except:
            log("[Bouquets::get_bouquet_list] error: cannot get bouquet list!")
            return None

        # check for error codes
        try:
            e
        except NameError:
            # no error, open the url
            try:
                handle = urllib2.urlopen(req)
            except:
                log("[Bouquets::get_bouquet_list] error: cannot get bouquet list!")
                return None
        else:
            # check for other errors then 401 (authorization required)    
            if e.code == 401:
                # check for an www-authenticate line
                authline = e.headers.get('www-authenticate', '')
                if not authline:
                    log("[Bouquets::get_bouquet_list] error: no authentication response header found!")
                    return None
   
                # this regular expression is used to extract scheme and realm 
                authobj = re.compile(r'''(?:\s*www-authenticate\s*:)?\s*(\w*)\s+realm=['"](\w+)['"]''', re.IGNORECASE)
                matchobj = authobj.match(authline)
                if not matchobj:
                    log("[Bouquets::get_bouquet_list] error: the authentication line is badly formed!")
                    return None

                scheme = matchobj.group(1) 
                realm = matchobj.group(2)
                if scheme.lower() != 'basic':
                    log("[Bouquets::get_bouquet_list] error: no basic authentication method!")
                    return None

                # base64 encode the username and password and sent it to the server
                base64string = base64.encodestring('%s:%s' % (enigma2_username, enigma2_password))[:-1]
                authheader =  "Basic %s" % base64string
                req.add_header("Authorization", authheader)
                try:
                    handle = urllib2.urlopen(req)
                except IOError, e:
                    log("[Bouquets::get_bouquet_list] error: enigma2_username or enigma2_password is wrong!")
                    return None
            else:
                try:
                    handle = urllib2.urlopen(req)
                except:
                    log("[Bouquets::get_bouquet_list] error: cannot get bouquet list!")
                    return None


        # read the http content
        content = handle.read()

        if debug:
            log("[Bouquets::get_bouquet_list] debug: channel list" + content)

        # reset the self.bouquets var
        self.bouquets = None
        self.bouquets = []

        # get the bouqetlist
        doc = libxml2.parseMemory(content, len(content))
        root = doc.getRootElement()
        e2servicelist = root.children

        # loop the first elements
        while e2servicelist is not None:
            if debug:
                log("[Bouquets::get_bouquet_list] debug: e2servicelist  data [" + str(e2servicelist) + "]")

            if e2servicelist.type == "element":
                if e2servicelist.name == "e2service":
                    if debug:
                        log("[Bouquets::get_bouquet_list] debug: element1 found! name [" + e2servicelist.name + "]" + " content [" + e2servicelist.content + "]")

                    e2service = e2servicelist.children

                    # reset the bouquet vars
                    name = None
                    ref = None

                    # loop the second elements (last)
                    while e2service is not None:
                        if e2service.type == "element":
                            if debug:
                                log("[Bouquets::get_bouquet_list] debug: element2 found! name [" + e2service.name + "]" + " content [" + e2service.content + "]")

                            if e2service.name == "e2servicereference":
                                ref = e2service.content

                            if e2service.name == "e2servicename":
                                name = e2service.content

                        e2service = e2service.next

                    # if vars are set append them to the bouquets array
                    if name and ref:
                        # store the bouquet
                        self.bouquets.append(Bouquet(name,ref))

            e2servicelist = e2servicelist.next

        doc.freeDoc()

        if len(self.bouquets) < 1:
            return None

        return True

    def list_bouquets(self):
        """
        Function that returns a options table with all the channels listed in the bouquet
        """

        if debug:
            log("[Bouquets::list_bouquets] debug: entering function")

        id = 0

        html = ""
        html += "<script language=\"javascript\">\n"
        html += "function change_bouquet() {\n"
        html += "    bid = document.bouquet_select.bouquet_selection.options[document.bouquet_select.bouquet_selection.selectedIndex].value;\n"
        html += "    location.href='/bouquet='+bid;\n}\n"
        html += "</script>\n\n"
        html += "<form name=\"bouquet_select\">\n"
        html += "<b>Bouquet:</b>\n&nbsp\n"
        html += "<select name=\"bouquet_selection\" onChange=\"javascript:change_bouquet();\">\n"

        for bouquet in self.bouquets:
            if self.active_bouquet == id:
                html += "<option value=%di selected>" % id + " " + bouquet.name + "</option>\n"
            else:
                html += "<option value=%d>" % id + " " + bouquet.name + "</option>\n"

            id += 1

        html += "</select>\n</form>\n"

        return html

    def set_active_bouquet(self,bouquet_id):
        """
        Function that sets the bouquet and returns the name and ref
        """

        if debug:
            log("[Bouquets::set_active_bouquet] debug: entering function")

        if debug:
            log("[Bouquets::set_active_bouquet] debug: set bouquet to id [%d]" % bouquet_id)

        self.active_bouquet = bouquet_id

        bouquet = [self.bouquets[self.active_bouquet].name, self.bouquets[self.active_bouquet].ref]

        return bouquet


###################################################################################
### Channel classes
###################################################################################

class Channel:
    def __init__(self, name, stream):
        self.name = name
        self.stream = stream

class Channels(object):
    def __init__(self):
        self.channels = []

        #
        # Keeps track of the active channel
        # max_channels = no transcoding
        #
        self.active_channel = max_channels

        # vlc subprocess object
        self.vlc_proc = None

    def refresh_channel_list(self,bouquet_name,bouquet_ref):
        """
        Function which fetches and store the recent channel list

        API url:
          http://<enigma host>/web/services.m3u?bRef=<url_encoded_ref>

        Return values:
          #EXTINF:-1,<channel_name>
          http://<enigma host>:8001/<ref>
        """

        if debug:
            log("[Channels::refresh_channel_list] debug: entering function")

        if enigma2_use_ssl == "yes":
            req_url = "https://" + enigma2_host + ":" + "%d" % enigma2_port + "/web/services.m3u?bRef=" + urllib.quote(bouquet_ref)
        else:
            req_url = "http://" + enigma2_host + ":" + "%d" % enigma2_port + "/web/services.m3u?bRef=" + urllib.quote(bouquet_ref)

        if debug:
            log("[Channels::get_channel_list] debug: opening url: " + req_url)

        req = urllib2.Request(req_url)
        try:
            handle = urllib2.urlopen(req)
        except IOError, e:
            pass
        except:
            log("[Channels::get_channel_list] error: cannot get bouquet list!")
            return None

        # check for error codes
        try:
            e
        except NameError:
            # no error, open the url
            try:
                handle = urllib2.urlopen(req)
            except:
                log("[Channels::get_channel_list] error: cannot refresh channel list!")
                return None
        else:
            # check for other errors then 401 (authorization required)    
            if e.code == 401:
                # check for an www-authenticate line
                authline = e.headers.get('www-authenticate', '')
                if not authline:
                    log("[Channels::get_channel_list] error: no authentication response header found!")
                    return None
   
                # this regular expression is used to extract scheme and realm 
                authobj = re.compile(r'''(?:\s*www-authenticate\s*:)?\s*(\w*)\s+realm=['"](\w+)['"]''', re.IGNORECASE)
                matchobj = authobj.match(authline)
                if not matchobj:
                    log("[Channels::get_channel_list] error: the authentication line is badly formed!")
                    return None

                scheme = matchobj.group(1) 
                realm = matchobj.group(2)
                if scheme.lower() != 'basic':
                    log("[Channels::get_channel_list] error: no basic authentication method!")
                    return None

                # base64 encode the username and password and sent it to the server
                base64string = base64.encodestring('%s:%s' % (enigma2_username, enigma2_password))[:-1]
                authheader =  "Basic %s" % base64string
                req.add_header("Authorization", authheader)
                try:
                    handle = urllib2.urlopen(req)
                except IOError, e:
                    log("[Channels::get_channel_list] error: enigma2_username or enigma2_password is wrong!")
                    return None
            else:
                try:
                    handle = urllib2.urlopen(req)
                except:
                    log("[Channels::get_channel_list] error: cannot refresh channel list!")
                    return None

        # read the http content
        content = handle.read()

        if debug:
            log("[Channels::get_channel_list] debug: channel list" + content)

        if not content:
            return None

        # reset the self.channels var
        self.channels = None
        self.channels = []

        # store the name and stream url
        ni = None
        for line in content.split('\n'):
            if line[:7] == "#EXTINF":
                name = line.split(',')[1]
                ni = True
            else:
                if ni:
                    self.channels.append(Channel(name,line))
                    ni = None

        if len(self.channels) < 1:
            return None

        return True

    def list_channels(self):
        """
        Function which returns a html table with all the channels listed in the bouquet
        """

        if debug:
            log("[Channels::list_channels] debug: entering function")

        id = 0

        html = ""
        html += "<script language=\"javascript\">\n"
        html += "function change_channel() {\n"
        html += "    cid = document.channel_select.channel_selection.options[document.channel_select.channel_selection.selectedIndex].value;\n"
        html += "    location.href='/start='+cid;\n}\n"
        html += "</script>\n\n"
        html += "<form name=\"channel_select\">\n"
        html += "<b>Channel:</b>\n&nbsp\n"
        html += "<select name=\"channel_selection\">\n"

        for channel in self.channels:
            if self.active_channel == id:
                html += "<option value=%di selected>" % id + " " + channel.name + "</option>\n"
            else:
                html += "<option value=%d>" % id + " " + channel.name + "</option>\n"

            id += 1

        html += "</select>\n"

        # check if there is a active transcoding process
        if self.active_channel < max_channels:
            html += "<input type=button name=\"stop_channel\" value=\"stop stream\" onClick=\"location.href='/stop';\">\n"
        else:
            html += "<input type=button name=\"start_channel\" value=\"start stream\" onClick=\"javascript:change_channel();\">\n"

        html += "</form>\n"

        return html

    def play_channel(self,id):
        """
        Function which launches the vlc transcoding process with the selected stream
        """

        if debug:
            log("[Channels::play_channel] debug: entering function")

        if self.active_channel < max_channels:
            log("[Channels::play_channel] error: " + self.channels[self.active_channel].name  + " is already playing!")

            return

        if len(self.channels) < 1:
            log("[Channels::play_channel] error: no channels stored in array!")

            return

        if debug == 1:
            log("[Channels::play_channel] debug: transcoding channel id[%d" % id + "] / name[" + self.channels[id].name  + "] / stream[" + self.channels[id].stream + "]")

        # construct the VLC command
        cmd = vlc_exe + " \"" + self.channels[id].stream + "\" --sout '#transcode{" + vlc_stream_options  + "}:standard{access=http,mux=ts,dst=" + vlc_http_stream_bind_addr + ":%d}'" % vlc_http_stream_bind_port # + " > /dev/null 2>&1 &"

        if debug == 1:
            log("[Channels::play_channel] debug: launching transcoding process with command [" + cmd + "]")

        # start the VLC process
        self.vlc_proc = subprocess.Popen(cmd, shell=True)

        self.active_channel = id

        return

    def stop_channel(self):
        """
        Function which stops the vlc transcoding process
        """

        if debug:
            log("[Channels::stop_channel] debug: entering function")

        if self.active_channel == max_channels:
            log("[Channels::stop_channel] error: no channel playing!")

            return None

        # shutdown VLC
        self.vlc_proc.send_signal(signal.SIGINT)

        # wait for it, otherwise it turns into a zombie
        self.vlc_proc.wait()

        # set the active channel to "not active"
        self.active_channel = max_channels

        return True

    def get_active_channel(self):
        """
        Function to get the active channel
        """

        if debug:
            log("[Channels::get_active_channel] debug: entering function")

        return self.active_channel

    def get_active_channel_name(self):
        """
        Function to get the active channel
        """

        if debug:
            log("[Channels::get_active_channel_name] debug: entering function")

        if self.active_channel < max_channels:
            return self.channels[self.active_channel].name
        else:
            return None


###################################################################################
### Main
###################################################################################

# store the logo file full path
logo_file_path = openetv_dir + "/" + logo_file

# check if the logo image file can be found
if not os.path.isfile(logo_file_path):
    print "error: logo image file not found at \"" + logo_file_path + "\""
    print "       maybe the openetv_dir variable isn't configured correctly?"
    sys.exit(2)

# store the log file full path
log_file_path = openetv_dir + "/" + log_file

# check if we can write the logfile
try:
    f = open(log_file_path,'a')
except IOError:
    print "error: cannot write to logfile \"" + log_file_path + "\""
    sys.exit(2)

f.close

# store the pid file full path
pid_file_path = openetv_dir + "/" + pid_file

# check if the vlc executable exists
if not os.path.isfile(vlc_exe):
    print "error: vlc executable not found at \"" + vlc_exe + "\""
    sys.exit(2)

app = App()
if len(sys.argv) == 2:
    if 'start' == sys.argv[1]:
        log("[Main] OpenETV started.")
        app.start()
    elif 'stop' == sys.argv[1]:
        log("[Main] OpenETV stopped.")
        app.stop()
    elif 'restart' == sys.argv[1]:
        log("[Main] OpenETV restarted.")
        app.restart()
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
else:
    print "usage: %s start|stop|restart" % sys.argv[0]
    sys.exit(2)
