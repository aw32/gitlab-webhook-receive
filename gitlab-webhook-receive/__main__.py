#!/usr/bin/env python -u

import os
import sys
import json
import signal
import argparse
from . import *

reqiored_arguments = ['interface', 'port', 'config']

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        prog='fsmiweb_services.hyde',
        description='Serve Gitlab Hook and execute commands',
        argument_default=argparse.SUPPRESS
    )
    parser.add_argument(
        '--config',
        help='Path to config file'
    )
    parser.add_argument(
        '--interface',
        help='Address to listen on'
    )
    parser.add_argument(
        '--port',
        type=int,
        help='Port to listen on'
    )

    args = parser.parse_args()
    args = vars(args)

    if 'config' not in args:
        print("Config missing")
        parser.print_help()
        sys.exit(1)
    config = None
    try:
        with open(args['config'], 'r') as f:
            configtext = f.read()
            config = json.loads(configtext)
    except Exception as e:
        print("Failed to read config file", e)
        sys.exit(1)

    interface = None
    if 'interface' in config:
        interface = config['interface']
    if 'interface' in args:
        port = args['interface']
    if interface == None:
        print('interface missing')
        sys.exit(1)
    port = None
    if 'port' in config:
        port = config['port']
    if 'port' in args:
        port = args['port']
    if port == None:
        print('port missing')
        sys.exit(1)

    print("Starting")
    server = GitlabHookServer(interface, port, config)
    server.start()
    signal.sigwait([signal.SIGINT,signal.SIGTERM])
    print("Shutting down")
    server.stopServer()


