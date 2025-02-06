import secrets
import sys
import textwrap

from passlib.hash import pbkdf2_sha512

from odoo.cli import Command
from odoo.tools import config


class GenProxyToken(Command):
    """ Generate and (re)set proxy access token in config file """

    def generate_token(self, length=16):
        token = secrets.token_hex(int(length / 2))
        split_size = int(length / 4)
        return '-'.join(textwrap.wrap(token, split_size))

    def run(self, cmdargs):
        self.parser.add_argument('-c', '--config', type=str, help="Specify an alternate config file")
        self.parser.add_argument('--token-length', type=int, help="Token Length", default=16)
        args, _ = self.parser.parse_known_args()
        if args.config:
            config.rcfile = args.config
        token = self.generate_token(length=args.token_length)
        config['proxy_access_token'] = pbkdf2_sha512.hash(token)
        config.save()
        sys.stdout.write(f'{token}\n')
