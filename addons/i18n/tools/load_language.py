from odoo.addons.i18n.cli.i18n import get_languages
from odoo.cli.command import Command
from odoo.tools.translate import load_language


class LoadLang(Command):
    """
    Load selected languages

    This command is not shown on `help` because it's not imported by the `__init__.py` file.
    We can use it by passing the file through the `odoo-bin shell`.

    ./odoo-bin \
        --addons-path=odoo/addons,addons   \
        shell                              \
        -c ../.odoorc                      \
        --                                 \
        --languages it_IT fr_BE            \
        < addons/i18n/tools/load_lanaguage.py
    """
    description = 'Install languages'

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.env = kwargs.get('env')
        self.parser.add_argument(
            '--languages', nargs='*',
            help=('List of ISO codes to be installed.'))

    def run(self, cmdargs):
        try:
            parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)
        except ValueError as e:
            self.parser.print_help()
            Command.die(f'\n{e}\n')

        # Start a new environment, create/init the database if needed
        for language in get_languages(self.env, parsed_args.languages):
            load_language(self.env.cr, language.code)
        self.env.cr.commit()


LoadLang(env=self.env).run(cmdargs=shellargs)
