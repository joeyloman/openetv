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
import base64

from bouquets import Bouquets
from channels import Channels

#openetv_version = "201601403"

def get_version(openetv_config):
    f = open(openetv_config['openetv']['openetv_dir'] + "/VERSION", 'r')
    version = f.read()
    f.close()

    return version

def html_header(openetv_config):
    openetv_version = get_version(openetv_config)

    html = "<html>\n"
    html += "<head>\n"
    html += "<title>\n"
    html += "OpenETV version " + openetv_version
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

    f = open(openetv_config['openetv']['openetv_dir'] + "/openetv_images/logo-app.png", 'r')
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

def html_menu(openetv_config, vlc_quality, active_channel, active_channel_name, max_channels):
    html = "<script language=\"javascript\">\n"
    html += "function change_quality() {\n"
    html += "    qs = document.quality_select.quality_selection.options[document.quality_select.quality_selection.selectedIndex].value;\n"
    html += "    location.href='/quality='+qs;\n}\n"
    html += "</script>\n\n"
    html += "<form name=\"quality_select\">\n"
    html += "<b>Transcoding quality:</b>\n&nbsp\n"
    html += "<select name=\"quality_selection\" onChange=\"javascript:change_quality();\">\n"

    if vlc_quality == "poor":
        html += "<option value=poor selected>poor</option>\n"
        html += "<option value=medium>medium</option>\n"
        html += "<option value=good>good</option>\n"
    elif vlc_quality == "medium":
        html += "<option value=poor>poor</option>\n"
        html += "<option value=medium selected>medium</option>\n"
        html += "<option value=good>good</option>\n"
    else:
        html += "<option value=poor>poor</option>\n"
        html += "<option value=medium>medium</option>\n"
        html += "<option value=good selected>good</option>\n"
    html += "</select>\n</form>\n"

    html += "<form>\n"

    html += "<input type=button value='refresh bouquet list' onClick=location.href='/refresh=bouquet'>\n"
    html += "<input type=button value='refresh channel list' onClick=location.href='/refresh=channel'>\n"

    html += "</form>\n"

    if active_channel < max_channels:
        html += "<b>Now Playing: " + active_channel_name + "</b><br><br>\n"
        html += "<b>Stream: http://" + openetv_config['vlc']['vlc_http_stream_bind_addr'] + ":" + openetv_config['vlc']['vlc_http_stream_bind_port'] + "</b><br>\n"

    return html

def html_footer(openetv_config):
    openetv_version = get_version(openetv_config)

    html = "<br><i>OpenETV version " + openetv_version + " - <a href=\"http://www.openetv.org\" target=\"_blank\">http://www.openetv.org</a></i><br>\n"
    html += "</body>\n"
    html += "</html>\n"

    return html

def startservice(openetv_config, logging):
    # set startup defaults
    bouquet_id = 0
    bouquet_name = None
    bouquet_ref = None

    max_bouquets = 1000
    max_channels = 1000

    vlc_quality = "good"

    # create the bouquets and channels objects
    r_bouquets = Bouquets(openetv_config, logging)
    r_channels = Channels(openetv_config, logging, max_channels)

    # refresh bouquet list
    rb_res = r_bouquets.refresh_bouquet_list()

    # check if the bouquet list is successfully fetched
    if rb_res:
        # get bouquet list
        html_bouquets = r_bouquets.list_bouquets()

        # get bouquet name and ref
        bouquet = r_bouquets.set_active_bouquet(bouquet_id)
        bouquet_name = bouquet[0]
        bouquet_ref = bouquet[1]

        # refresh the channel list
        rc_res = r_channels.refresh_channel_list(bouquet_name, bouquet_ref)

        # socket/bind/listen setup
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((openetv_config['openetv']['bind_host'], int(openetv_config['openetv']['bind_port'])))
        s.listen(5)

        while True:
            c, addr = s.accept()

            logging.debug("[App::run] debug: incomming connection from: " + addr[0] + ":%d" % addr[1])

            # recieve HTTP command
            cmd = c.recv(1024).split('\n')[0]

            logging.debug("[App::run] debug: command [" + cmd + "]")

            if cmd[:3] == "GET":
                page = cmd.split(' ')[1]

                logging.debug("[App::run] debug: page request [" + page + "]")

                # get current active channels
                active_channel = r_channels.get_active_channel()
                active_channel_name = r_channels.get_active_channel_name()

                if page == "/" or page == "/index.htm" or page == "index.html":
                    """
                    Expected parameters: none
                    """

                    html = html_header(openetv_config)

                    if rb_res:
                        html += r_bouquets.list_bouquets()
                    else:
                        html += "<b>Error: could not get bouquet list!</b>"

                    if rc_res:
                        html += r_channels.list_channels()

                    html += html_menu(openetv_config, vlc_quality, active_channel, active_channel_name, max_channels)
                    html += html_footer(openetv_config)

                    write_data = "HTTP/1.1 200 OK\n"
                    write_data += "Content-Length: %d\n" % len(html)
                    write_data += "Content-Type: text/html\n\n"
                    write_data += html

                    c.send(write_data)
                elif page[:8] == "/quality":
                    """
                    Expected parameters: /quality=<poor|medium|good>
                    """

                    q_str = page.split('=')[1]

                    if q_str == "poor":
                        vlc_quality = "poor"
                    elif q_str == "medium":
                        vlc_quality = "medium"
                    else:
                        vlc_quality = "good"

                    logging.debug("[App::run] debug: quality changed to [" + q_str + "]")

                    html = html_header(openetv_config)

                    if rb_res:
                        html += r_bouquets.list_bouquets()
                    else:
                        html += "<b>Error: could not get bouquet list!</b>"

                    if rc_res:
                        html += r_channels.list_channels()

                    html += html_menu(openetv_config, vlc_quality, active_channel, active_channel_name, max_channels)
                    html += html_footer(openetv_config)

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

                    logging.debug("[App::run] debug: changing bouquet list to [" + bid + "]")

                    try:
                        id = int(bid)
                    except ValueError:
                        html = html_header(openetv_config)

                        if rb_res:
                            html += r_bouquets.list_bouquets()
                        else:
                            html += "<b>Error: could not get bouquet list!</b>"

                        html += html_menu(openetv_config, vlc_quality, active_channel, active_channel_name, max_channels)
                        html += "<b>Error: bouquet id is invalid!</b><br>"
                        html += html_footer(openetv_config)

                        write_data = "HTTP/1.1 200 OK\n"
                        write_data += "Content-Length: %d\n" % len(html)
                        write_data += "Content-Type: text/html\n\n"
                        write_data += html

                        c.send(write_data)
                        c.close()

                    if not 0 <= int(bid) < max_bouquets:
                        html = html_header(openetv_config)

                        if rb_res:
                            html += r_bouquets.list_bouquets()
                        else:
                            html += "<b>Error: could not get bouquet list!</b>"

                        html += html_menu(openetv_config, vlc_quality, active_channel, active_channel_name, max_channels)
                        html += "<b>Error: bouquetplaylist id is not in range between 0 and 999!</b><br>"
                        html += html_footer(openetv_config)

                        write_data = "HTTP/1.1 200 OK\n"
                        write_data += "Content-Length: %d\n" % len(html)
                        write_data += "Content-Type: text/html\n\n"
                        write_data += html

                        c.send(write_data)
                        c.close()

                    if rb_res:
                        # select bouquet
                        bouquet_id = id
                        bouquet = r_bouquets.set_active_bouquet(bouquet_id)
                        bouquet_name = bouquet[0]
                        bouquet_ref = bouquet[1]

                    html = html_header(openetv_config)

                    if rb_res:
                        html += r_bouquets.list_bouquets()
                    else:
                        html += "<b>Error: could not get bouquet list!</b>"

                    # refresh the channels
                    rc_res = r_channels.refresh_channel_list(bouquet_name, bouquet_ref)
                    if rc_res:
                        html += r_channels.list_channels()

                    html += html_menu(openetv_config, vlc_quality, active_channel, active_channel_name, max_channels)
                    html += html_footer(openetv_config)

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

                    logging.debug("[App::run] debug: start channel id [" + cid + "]")

                    try:
                        id = int(cid)
                    except ValueError:
                        html = html_header(openetv_config)

                        if rb_res:
                            html += r_bouquets.list_bouquets()
                        else:
                            html += "<b>Error: could not get bouquet list!</b>"

                        html += html_menu(openetv_config, vlc_quality, active_channel, active_channel_name, max_channels)
                        html += "<b>Error: playlist id is invalid!</b><br>"
                        html += html_footer(openetv_config)

                        write_data = "HTTP/1.1 200 OK\n"
                        write_data += "Content-Length: %d\n" % len(html)
                        write_data += "Content-Type: text/html\n\n"
                        write_data += html

                        c.send(write_data)
                        c.close()

                    if not 0 <= int(id) < max_channels:
                        html = html_header(openetv_config)

                        if rb_res:
                            html += r_bouquets.list_bouquets()
                        else:
                            html += "<b>Error: could not get bouquet list!</b>"

                        html += html_menu(openetv_config, vlc_quality, active_channel, active_channel_name, max_channels)
                        html += "<b>Error: playlist id is not in range between 0 and 999!</b><br>"
                        html += html_footer(openetv_config)

                        write_data = "HTTP/1.1 200 OK\n"
                        write_data += "Content-Length: %d\n" % len(html)
                        write_data += "Content-Type: text/html\n\n"
                        write_data += html

                        c.send(write_data)
                        c.close()

                    html = html_header(openetv_config)

                    if rb_res:
                        html += r_bouquets.list_bouquets()
                    else:
                        html += "<b>Error: could not get bouquet list!</b>"

                    # play the selected channel
                    r_channels.play_channel(id, vlc_quality)

                    # get current active channels
                    active_channel = r_channels.get_active_channel()
                    active_channel_name = r_channels.get_active_channel_name()

                    if rc_res:
                        html += r_channels.list_channels()

                    html += html_menu(openetv_config, vlc_quality, active_channel, active_channel_name, max_channels)
                    html += html_footer(openetv_config)

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

                    logging.debug("[App::run] debug: stop channel id [%d" % active_channel + "]")

                    if active_channel < max_channels:
                        html = html_header(openetv_config)

                        if rb_res:
                            html += r_bouquets.list_bouquets()
                        else:
                            html += "<b>Error: could not get bouquet list!</b>"

                        # stop the transcoding process
                        stop_res = r_channels.stop_channel()

                        # get current active channels
                        active_channel = r_channels.get_active_channel()
                        active_channel_name = r_channels.get_active_channel_name()

                        if rc_res:
                            html += r_channels.list_channels()

                        html += html_menu(openetv_config, vlc_quality, active_channel, active_channel_name, max_channels)

                        if not stop_res:
                            html += "<b>Error: unable to stop stream, nothing is playing!</b><br>\n"

                        html += html_footer(openetv_config)
                    else:
                        html = html_header(openetv_config)

                        if rb_res:
                            html += r_bouquets.list_bouquets()
                        else:
                            html += "<b>Error: could not get bouquet list!</b>"

                        if rc_res:
                            html += r_channels.list_channels()

                        html += html_menu(openetv_config, vlc_quality, active_channel, active_channel_name, max_channels)
                        html += html_footer(openetv_config)

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

                    html = html_header(openetv_config)

                    # refresh bouquets
                    if type == "bouquet":
                        rb_res = r_bouquets.refresh_bouquet_list()

                    if rb_res:
                        html += r_bouquets.list_bouquets()

                        # refresh the channel list
                        if type == "channel":
                            rc_res = r_channels.refresh_channel_list(bouquet_name, bouquet_ref)

                        if rc_res:
                            html += r_channels.list_channels()
                    else:
                        html += "<b>Error: could not get bouquet list!</b>"

                    html += html_menu(openetv_config, vlc_quality, active_channel, active_channel_name, max_channels)
                    html += html_footer(openetv_config)

                    write_data = "HTTP/1.1 200 OK\n"
                    write_data += "Content-Length: %d\n" % len(html)
                    write_data += "Content-Type: text/html\n\n"
                    write_data += html

                    c.send(write_data)

            logging.debug("[App::run] closing connection")

            c.close()
