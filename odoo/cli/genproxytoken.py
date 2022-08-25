import argparse
import os
import secrets
import sys
import textwrap

from passlib.hash import pbkdf2_sha512

from . import Command
from odoo.tools import config


class GenProxyToken(Command):
    def __init__(self):
        self.command_name = "genproxytoken"

    def generate_token(self, length=16):
        token = secrets.token_hex(int(length / 2))
        split_size = int(length / 4)
        return '-'.join(textwrap.wrap(token, split_size))

    def run(self, cmdargs):
        parser = argparse.ArgumentParser(
            prog="%s %s" % (sys.argv[0].split(os.path.sep)[-1], self.command_name),
            description="Generate and (re)set proxy access token in config file"
        )
        parser.add_argument('-c', '--config', type=str, help="Specify an alternate config file")
        parser.add_argument('--token-length', type=int, help="Token Length", default=16)
        args, _ = parser.parse_known_args()
        if args.config:
            config.rcfile = args.config
        token = self.generate_token(length=args.token_length)
        config['proxy_access_token'] = pbkdf2_sha512.hash(token)
        config.save()
        sys.stdout.write(f'{token}\n')
