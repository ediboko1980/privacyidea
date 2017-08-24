# -*- coding: utf-8 -*-
#
#  2017-08-23 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial federation handler
#
# License:  AGPLv3
# (c) 2017. Cornelius Kölbel
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
__doc__ = """This is the event handler module for privacyIDEA federations.
Requests can be forwarded to other privacyIDEA servers.
"""
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib.privacyideaserver import (get_privacyideaservers,
                                               get_privacyideaserver)
from privacyidea.lib import _
import json
import logging
import requests
from flask import jsonify


log = logging.getLogger(__name__)


class ACTION_TYPE(object):
    """
    Allowed actions
    """
    FORWARD = "forward"


class FederationEventHandler(BaseEventHandler):
    """
    An Eventhandler needs to return a list of actions, which it can handle.

    It also returns a list of allowed action and conditions

    It returns an identifier, which can be used in the eventhandlig definitions
    """

    identifier = "Federation"
    description = "This event handler can forward the request to other " \
                  "privacyIDEA servers"

    @property
    def actions(cls):
        """
        This method returns a dictionary of allowed actions and possible
        options in this handler module.

        :return: dict with actions
        """
        pi_servers = [x.config.identifier for x in get_privacyideaservers()]
        actions = {ACTION_TYPE.FORWARD:
                       {"privacyIDEA":
                            {"type": "str",
                             "required": True,
                             "value": pi_servers,
                             "description": _("The remote/child privacyIDEA "
                                              "Server.")
                             },
                        "realm":
                            {"type": "str",
                             "description": _("Change the realm name to a "
                                              "realm on the child privacyIDEA "
                                              "system.")
                            },
                        "resolver":
                            {"type": "str",
                             "description": _("Change the resolver name to a "
                                              "resolver on the child "
                                              "privacyIDEA system.")
                            },
                        "forward_client_ip":
                            {"type": "bool",
                             "description": _("Forward the client IP to the "
                                              "child privacyIDEA server. "
                                              "Otherwise this server will "
                                              "be the client.")
                            }
                        }
                   }
        return actions

    def do(self, action, options=None):
        """
        This method executes the defined action in the given event.

        :param action:
        :param options: Contains the flask parameters g, request, response
            and the handler_def configuration
        :type options: dict
        :return:
        """
        request = options.get("request")
        handler_def = options.get("handler_def")
        handler_options = handler_def.get("options", {})

        if handler_def.get("action") == ACTION_TYPE.FORWARD:
            server_def = handler_options.get("privacyIDEA")
            pi_server = get_privacyideaserver(server_def)

            # the new url is the configured server url and the original path
            url = pi_server.config.url + request.path
            # We use the originial method
            method = request.method
            tls = pi_server.config.tls
            # We also transfer the original payload
            data = request.all_data

            # TODO: We need to pass an authoriztaion header if we forward
            # administrative requests
            log.info(u"Sending {0} request to {1!r}".format(method, url))
            requestor = None
            params = None
            if method.upper() == "GET":
                params = data
                data = None
                requestor = requests.get
            elif method.upper() == "POST":
                requestor = requests.post
            elif method.upper() == "DELETE":
                requestor = requests.delete

            if requestor:
                r = requestor(url, params=params, data=data, verify=tls)
                # convert requests Response to werkzeug Response
                response_dict = json.loads(r.text)
                if "detail" in response_dict:
                    response_dict.get("detail")["origin"] = url
                # We will modify the response!
                options["response"] = jsonify(response_dict)
            else:
                log.warning(u"Unsupported method: {0!r}".format(method))

        return True
