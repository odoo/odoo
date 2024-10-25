import sys

from .cli.command import Command

import odoo


def main():

    command_name = 'server'

    _program, *all_args = sys.argv
    match all_args:
        case first_arg, *args:

            if not first_arg.startswith('-'):
                command_name = first_arg

            elif first_arg.startswith('--addons-path='):
                # The only shared option is '--addons-path=' needed
                # to discover additional commands from modules
                # Parse only the addons-path, do not setup the logger...
                odoo.tools.config._parse_config([first_arg])

    if command := Command.find_command(command_name):
        command().run(args)
    else:
        sys.exit('Unknown command %r' % command)


if __name__ == "__main__":
    main()
