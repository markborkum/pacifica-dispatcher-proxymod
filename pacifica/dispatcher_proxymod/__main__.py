#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# pacifica-dispatcher-proxymod: pacifica/dispatcher_proxymod/__main__.py
#
# Copyright (c) 2019, Battelle Memorial Institute
# All rights reserved.
#
# See LICENSE and WARRANTY for details.
"""Main method for starting proxymod handler."""
import argparse
import os
from time import sleep
from threading import Thread

import cherrypy
import playhouse.db_url

from pacifica.dispatcher.receiver import create_peewee_model

from .router import router

# pylint: disable=invalid-name
ReceiveTaskModel = create_peewee_model(playhouse.db_url.connect(os.getenv('DATABASE_URL', 'sqlite:///:memory:')))

ReceiveTaskModel.create_table(safe=True)

celery_app = ReceiveTaskModel.create_celery_app(
    router, 'pacifica.dispatcher_proxymod.app', 'pacifica.dispatcher_proxymod.tasks.receive',
    backend=os.getenv('BACKEND_URL', 'rpc://'), broker=os.getenv('BROKER_URL', 'pyamqp://')
)

application = ReceiveTaskModel.create_cherrypy_app(celery_app.tasks['pacifica.dispatcher_proxymod.tasks.receive'])
# pylint: enable=invalid-name


def stop_later(doit=False):
    """Used for unit testing stop after 10 seconds."""
    if not doit:  # pragma: no cover
        return

    def sleep_then_exit():
        """sleep for 10 seconds then call cherrypy exit."""
        sleep(10)
        cherrypy.engine.exit()
    sleep_thread = Thread(target=sleep_then_exit)
    sleep_thread.daemon = True
    sleep_thread.start()


def main() -> None:
    """Main method for starting proxymod handler server."""
    parser = argparse.ArgumentParser(description='Start the CherryPy application and listen for connections.')
    parser.add_argument('--config', metavar='CONFIG', dest='config', type=str, default=None,
                        help='The CherryPy configuration file (overrides host and port options).')
    parser.add_argument('--host', metavar='HOST', dest='host', type=str, default='127.0.0.1',
                        help='The hostname or IP address on which to listen for connections.')
    parser.add_argument('--port', metavar='PORT', dest='port', type=int, default=8069,
                        help='The TCP port on which to listen for connections.')
    parser.add_argument('--stop-after-a-moment', help=argparse.SUPPRESS,
                        default=False, dest='stop_later',
                        action='store_true')
    args = parser.parse_args()
    stop_later(args.stop_later)
    cherrypy.config.update({
        'global': {
            'server.socket_host': args.host,
            'server.socket_port': args.port,
        },
    })

    if args.config is not None:  # pragma: no cover standard config update
        cherrypy.config.update(args.config)

    cherrypy.tree.mount(application)

    cherrypy.engine.start()
    cherrypy.engine.block()


__all__ = ('ReceiveTaskModel', 'application', 'celery_app', 'main', )

if __name__ == '__main__':
    main()
