from .command import Command, commands, load_addons_commands, load_internal_commands

import odoo.release


class Help(Command):
    """ Display the list of available commands """

    template = """\
usage: {prog_name} [--addons-path=PATH,...] <command> [...]

Odoo {version}
Available commands:

{command_list}

Use '{prog_name} server --help' for regular server options.
Use '{prog_name} <command> --help' for other individual commands options.
"""

    def run(self, args):
        load_internal_commands()
        load_addons_commands()

        padding = max(len(cmd_name) for cmd_name in commands) + 2
        name_desc = [
            (cmd_name, (cmd.__doc__ or "").strip())
            for cmd_name, cmd in sorted(commands.items())
        ]
        command_list = "\n".join(f"    {name:<{padding}}{desc}" for name, desc in name_desc)

        print(Help.template.format(  # noqa: T201
            prog_name=self.prog_name,
            version=odoo.release.version,
            command_list=command_list,
        ))
