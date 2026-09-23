import secrets
import sys
import textwrap

from odoo.cli import Command
from odoo.libs.password import pbkdf2_sha512_hash
from odoo.tools import config


class GenProxyToken(Command):
    """Generate and (re)set proxy access token in config file"""

    def generate_token(self, length=16):
        token = secrets.token_hex(int(length / 2))
        split_size = int(length / 4)
        return "-".join(textwrap.wrap(token, split_size))

    def run(self, cmdargs):
        self.parser.add_argument(
            "-c", "--config", type=str, help="Specify an alternate config file"
        )
        self.parser.add_argument(
            "--token-length", type=int, help="Token Length", default=16
        )
        # `cmdargs`, not the implicit sys.argv[1:]: the latter still carries
        # the command name and every global flag `main()` stripped, so this
        # parsed argv the dispatcher had already consumed.
        args, _ = self.parser.parse_known_args(cmdargs)
        if args.config:
            config["config"] = args.config
        token = self.generate_token(length=args.token_length)
        config["proxy_access_token"] = pbkdf2_sha512_hash(token)
        config.save()
        sys.stdout.write(f"{token}\n")
