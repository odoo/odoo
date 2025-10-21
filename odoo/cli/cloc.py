import sys

from odoo.tools import cloc, config
from . import Command


class Cloc(Command):
    """ Count lines of code per modules """

    description = """
        Odoo cloc is a tool to count the number of relevant lines written
        in Python, Javascript or XML. This can be used as rough metric for
        pricing maintenance of customizations.

        It has two modes of operation, either by providing a path:

            odoo-bin cloc -p module_path

        Or by providing the name of a database:

            odoo-bin --addons-path=dirs cloc -d database

        In the latter mode, only the custom code is accounted for.
    """

    def run(self, args):
        self.parser.add_argument('--database', '-d', dest="database", help="Database name")
        self.parser.add_argument('--path', '-p', action='append', help="File or directory path")
        self.parser.add_argument('--verbose', '-v', action='count', default=0)
        opt, unknown = self.parser.parse_known_args(args + ['--no-http'])
        if not opt.database and not opt.path:
            self.parser.print_help()
            sys.exit()

        c = cloc.Cloc()
        if opt.database:
            if ',' in opt.database:
                sys.exit("-d/--database has multiple databases, please provide a single one")
            config.parse_config(['-d', opt.database] + unknown)
            c.count_database(config['db_name'][0])
        if opt.path:
            for i in opt.path:
                c.count_path(i)
        c.report(opt.verbose)
