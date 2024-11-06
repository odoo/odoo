from .command import commands

from . import Command


class Help(Command):
    """ Display the list of available commands """

    def documentation(self, **kwargs):
        return """
            Commands:

            {command_list}

            Use '{appname} <command> --help' for individual command help.
        """.format(**kwargs)

    def run(self, args):
        self.load_internal_commands()
        self.load_addons_commands()

        padding = max(len(cmd) for cmd in commands) + 4
        command_list = "\n".join([
            f"{'':<12}{name:<{padding}}{(command.__doc__ or '').strip()}"
            for name in sorted(commands)
            if (command := self.find_command(name))
        ]).lstrip()

        parser = self.new_parser(
            description=self.cleanup_string(
                self.documentation(
                    command_list=command_list,
                    appname=self.appname
                )
        ))
        parser.print_help()
