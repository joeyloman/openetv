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

import urllib
import urllib2
import subprocess
import os
import re
import base64
import signal
import ssl

from openetv_libs import vlc

class Channel(object):
    def __init__(self, name, stream):
        self.name = name
        self.stream = stream

class Channels(object):
    def __init__(self, openetv_config, logging, max_channels):
        self.openetv_config = openetv_config
        self.logging = logging

        # get enigma options
        self.enigma2_use_ssl = self.openetv_config['enigma']['enigma2_use_ssl']
        self.enigma2_host = self.openetv_config['enigma']['enigma2_host']
        self.enigma2_port = self.openetv_config['enigma']['enigma2_port']
        self.enigma2_username = self.openetv_config['enigma']['enigma2_username']
        self.enigma2_password = self.openetv_config['enigma']['enigma2_password']

        # get vlc options
        self.vlc_pidfile = self.openetv_config['vlc']['vlc_pidfile']
        self.vlc_exe = self.openetv_config['vlc']['vlc_exe']
        self.vlc_stream_options_poor = self.openetv_config['vlc']['vlc_stream_options_poor']
        self.vlc_stream_options_medium = self.openetv_config['vlc']['vlc_stream_options_medium']
        self.vlc_stream_options_good = self.openetv_config['vlc']['vlc_stream_options_good']
        self.vlc_http_stream_bind_addr = self.openetv_config['vlc']['vlc_http_stream_bind_addr']
        self.vlc_http_stream_bind_port = self.openetv_config['vlc']['vlc_http_stream_bind_port']

        self.channels = []

        self.max_channels = max_channels

        #
        # keeps track of the active channel
        # max_channels = no transcoding
        #
        self.active_channel = max_channels

        # vlc subprocess object
        self.vlc_proc = None

    def refresh_channel_list(self, bouquet_name, bouquet_ref):
        """
        Function which fetches and store the recent channel list

        API url:
          http://<enigma host>/web/services.m3u?bRef=<url_encoded_ref>

        Return values:
          #EXTINF:-1,<channel_name>
          http://<enigma host>:8001/<ref>
        """

        self.logging.debug("[Channels::refresh_channel_list] debug: entering function")

        if self.enigma2_use_ssl == "yes":
            # disable the SSL security error
            if hasattr(ssl, '_create_unverified_context'):
                ssl._create_default_https_context = ssl._create_unverified_context

            req_url = "https://" + self.enigma2_host + ":" + self.enigma2_port + "/web/services.m3u?bRef=" + urllib.quote(bouquet_ref)
        else:
            req_url = "http://" + self.enigma2_host + ":" + self.enigma2_port + "/web/services.m3u?bRef=" + urllib.quote(bouquet_ref)

        self.logging.debug("[Channels::get_channel_list] debug: opening url: " + req_url)

        req = urllib2.Request(req_url)
        try:
            urllib2.urlopen(req)
        except IOError, e:
            pass
        except:
            self.logging.info("[Channels::get_channel_list] error: cannot get bouquet list!")
            return None

        # check for error codes
        try:
            e
        except NameError:
            # no error, open the url
            try:
                handle = urllib2.urlopen(req)
            except:
                self.logging.info("[Channels::get_channel_list] error: cannot refresh channel list!")
                return None
        else:
            # check for other errors then 401 (authorization required)    
            if e.code == 401:
                # check for an www-authenticate line
                authline = e.headers.get('www-authenticate', '')
                if not authline:
                    self.logging.info("[Channels::get_channel_list] error: no authentication response header found!")
                    return None
   
                # this regular expression is used to extract scheme and realm 
                authobj = re.compile(r'''(?:\s*www-authenticate\s*:)?\s*(\w*)\s+realm=['"](\w+)['"]''', re.IGNORECASE)
                matchobj = authobj.match(authline)
                if not matchobj:
                    self.logging.info("[Channels::get_channel_list] error: the authentication line is badly formed!")
                    return None

                scheme = matchobj.group(1) 
                realm = matchobj.group(2)
                if scheme.lower() != 'basic':
                    self.logging.info("[Channels::get_channel_list] error: no basic authentication method!")
                    return None

                # base64 encode the username and password and sent it to the server
                base64string = base64.encodestring('%s:%s' % (self.enigma2_username, self.enigma2_password))[:-1]
                authheader =  "Basic %s" % base64string
                req.add_header("Authorization", authheader)
                try:
                    handle = urllib2.urlopen(req)
                except IOError, e:
                    self.logging.info("[Channels::get_channel_list] error: enigma2_username or enigma2_password is wrong!")
                    return None
            else:
                try:
                    handle = urllib2.urlopen(req)
                except:
                    self.logging.info("[Channels::get_channel_list] error: cannot refresh channel list!")
                    return None

        # read the http content
        content = handle.read()

        self.logging.debug("[Channels::get_channel_list] debug: channel list" + content)

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

        self.logging.debug("[Channels::list_channels] debug: entering function")

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
        if self.active_channel < self.max_channels:
            html += "<input type=button name=\"stop_channel\" value=\"stop stream\" onClick=\"location.href='/stop';\">\n"
        else:
            html += "<input type=button name=\"start_channel\" value=\"start stream\" onClick=\"javascript:change_channel();\">\n"

        html += "</form>\n"

        return html

    def play_channel(self, id, vlc_quality):
        """
        Function which launches the vlc transcoding process with the selected stream
        """

        self.logging.debug("[Channels::play_channel] debug: entering function")

        if self.active_channel < self.max_channels:
            self.logging.info("[Channels::play_channel] error: " + self.channels[self.active_channel].name  + " is already playing!")

            return

        if len(self.channels) < 1:
            self.logging.info("[Channels::play_channel] error: no channels stored in array!")

            return

        self.logging.debug("[Channels::play_channel] debug: transcoding channel id[%d" % id + "] / name[" + self.channels[id].name  + "] / stream[" + self.channels[id].stream + "]")

        # construct the VLC command
        if vlc_quality == "poor":
            cmd = self.vlc_exe + " \"" + self.channels[id].stream + "\" --sout '#transcode{" + self.vlc_stream_options_poor + "}:standard{access=http,mux=ts,dst=" + self.vlc_http_stream_bind_addr + ":" + self.vlc_http_stream_bind_port + "}'" # + " > /dev/null 2>&1 &"
        elif vlc_quality == "medium":
            cmd = self.vlc_exe + " \"" + self.channels[id].stream + "\" --sout '#transcode{" + self.vlc_stream_options_medium + "}:standard{access=http,mux=ts,dst=" + self.vlc_http_stream_bind_addr + ":" + self.vlc_http_stream_bind_port + "}'" # + " > /dev/null 2>&1 &"
        else:
            cmd = self.vlc_exe + " \"" + self.channels[id].stream + "\" --sout '#transcode{" + self.vlc_stream_options_good + "}:standard{access=http,mux=ts,dst=" + self.vlc_http_stream_bind_addr + ":" + self.vlc_http_stream_bind_port + "}'" # + " > /dev/null 2>&1 &"

        self.logging.debug("[Channels::play_channel] debug: launching transcoding process with command [" + cmd + "]")

        # start the VLC process
        self.vlc_proc = subprocess.Popen(cmd, shell=True)

        # write the pidfile
        vlc.write_vlc_pid(self.vlc_pidfile, self.vlc_proc.pid)

        self.active_channel = id

        return

    def stop_channel(self):
        """
        Function which stops the vlc transcoding process
        """

        self.logging.debug("[Channels::stop_channel] debug: entering function")

        if self.active_channel == self.max_channels:
            self.logging.info("[Channels::stop_channel] error: no channel playing!")

            return None

        # shutdown VLC (in some circumstances VLC doesn't shutdown properly. that's why we always send the SIGKILL signal).
        os.kill(vlc.get_vlc_pid(self.vlc_pidfile, self.logging), signal.SIGKILL)

        # wait for it, otherwise it turns into a zombie
        self.vlc_proc.wait()

        # remove the VLC pidfile
        vlc.remove_vlc_pid(self.vlc_pidfile)

        # set the active channel to "not active"
        self.active_channel = self.max_channels

        return True

    def get_active_channel(self):
        """
        Function to get the active channel
        """

        self.logging.debug("[Channels::get_active_channel] debug: entering function")

        return self.active_channel

    def get_active_channel_name(self):
        """
        Function to get the active channel
        """

        self.logging.debug("[Channels::get_active_channel_name] debug: entering function")

        if self.active_channel < self.max_channels:
            return self.channels[self.active_channel].name
        else:
            return None
