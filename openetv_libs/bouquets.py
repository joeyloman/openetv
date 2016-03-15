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

import urllib2
import libxml2
import re
import base64
import ssl

class Bouquet(object):
    def __init__(self, name, ref):
        self.name = name
        self.ref = ref

class Bouquets(object):
    def __init__(self, openetv_config, logging):
        self.openetv_config = openetv_config
        self.logging = logging

        self.enigma2_use_ssl = self.openetv_config['enigma']['enigma2_use_ssl']
        self.enigma2_host = self.openetv_config['enigma']['enigma2_host']
        self.enigma2_port = self.openetv_config['enigma']['enigma2_port']
        self.enigma2_username = self.openetv_config['enigma']['enigma2_username']
        self.enigma2_password = self.openetv_config['enigma']['enigma2_password']

        self.bouquets = []

        #
        # keeps track of the active bouquet
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

        self.logging.debug("[Bouquets::get_bouquet_list] debug: entering function")

        if self.enigma2_use_ssl == "yes":
            # disable the SSL security error
            if hasattr(ssl, '_create_unverified_context'):
                ssl._create_default_https_context = ssl._create_unverified_context

            req_url = "https://" + self.enigma2_host + ":" + self.enigma2_port + "/web/getservices"
        else:
            req_url = "http://" + self.enigma2_host + ":" + self.enigma2_port + "/web/getservices"

        self.logging.debug("[Bouquets::get_bouquet_list] debug: opening url: " + req_url)

        req = urllib2.Request(req_url)
        try:
            handle = urllib2.urlopen(req)
        except IOError, e:
            pass
        except:
            self.logging.info("[Bouquets::get_bouquet_list] error: cannot get bouquet list!")
            return None

        # check for error codes
        try:
            e
        except NameError:
            # no error, open the url
            try:
                handle = urllib2.urlopen(req)
            except:
                self.logging.info("[Bouquets::get_bouquet_list] error: cannot get bouquet list!")
                return None
        else:
            # check for other errors then 401 (authorization required)    
            if e.code == 401:
                # check for an www-authenticate line
                authline = e.headers.get('www-authenticate', '')
                if not authline:
                    self.logging.info("[Bouquets::get_bouquet_list] error: no authentication response header found!")
                    return None
   
                # this regular expression is used to extract scheme and realm 
                authobj = re.compile(r'''(?:\s*www-authenticate\s*:)?\s*(\w*)\s+realm=['"](\w+)['"]''', re.IGNORECASE)
                matchobj = authobj.match(authline)
                if not matchobj:
                    self.logging.info("[Bouquets::get_bouquet_list] error: the authentication line is badly formed!")
                    return None

                scheme = matchobj.group(1) 
                realm = matchobj.group(2)
                if scheme.lower() != 'basic':
                    self.logging.info("[Bouquets::get_bouquet_list] error: no basic authentication method!")
                    return None

                # base64 encode the username and password and sent it to the server
                base64string = base64.encodestring('%s:%s' % (self.enigma2_username, self.enigma2_password))[:-1]
                authheader =  "Basic %s" % base64string
                req.add_header("Authorization", authheader)
                try:
                    handle = urllib2.urlopen(req)
                except IOError, e:
                    self.logging.info("[Bouquets::get_bouquet_list] error: enigma2_username or enigma2_password is wrong!")
                    return None
            else:
                try:
                    handle = urllib2.urlopen(req)
                except:
                    self.logging.info("[Bouquets::get_bouquet_list] error: cannot get bouquet list!")
                    return None


        # read the http content
        content = handle.read()

        self.logging.debug("[Bouquets::get_bouquet_list] debug: channel list" + content)

        # reset the self.bouquets var
        self.bouquets = None
        self.bouquets = []

        # get the bouqetlist
        doc = libxml2.parseMemory(content, len(content))
        root = doc.getRootElement()
        e2servicelist = root.children

        # loop the first elements
        while e2servicelist is not None:
            self.logging.debug("[Bouquets::get_bouquet_list] debug: e2servicelist  data [" + str(e2servicelist) + "]")

            if e2servicelist.type == "element":
                if e2servicelist.name == "e2service":
                    self.logging.debug("[Bouquets::get_bouquet_list] debug: element1 found! name [" + e2servicelist.name + "]" + " content [" + e2servicelist.content + "]")

                    e2service = e2servicelist.children

                    # reset the bouquet vars
                    name = None
                    ref = None

                    # loop the second elements (last)
                    while e2service is not None:
                        if e2service.type == "element":
                            self.logging.debug("[Bouquets::get_bouquet_list] debug: element2 found! name [" + e2service.name + "]" + " content [" + e2service.content + "]")

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

        self.logging.debug("[Bouquets::list_bouquets] debug: entering function")

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

    def set_active_bouquet(self, bouquet_id):
        """
        Function that sets the bouquet and returns the name and ref
        """

        self.logging.debug("[Bouquets::set_active_bouquet] debug: entering function")

        self.logging.debug("[Bouquets::set_active_bouquet] debug: set bouquet to id [%d]" % bouquet_id)

        self.active_bouquet = bouquet_id

        bouquet = [self.bouquets[self.active_bouquet].name, self.bouquets[self.active_bouquet].ref]

        return bouquet