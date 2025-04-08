import logging

from odoo import tools
from odoo.cli.command import Command, Subcommand
from odoo.modules.loading import force_demo


_logger = logging.getLogger(__name__)


class ModuleDemo(Subcommand):
    """ Install demo data """
    description = 'Install demo data'
    allow_config_file = True

    def run(self, cmdargs):
        parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)
        for db_name in tools.config['db_name']:
            with self.build_env(db_name) as env:
                force_demo(env)


class ModuleInstall(Subcommand):
    """ Install Odoo modules """
    description = 'Install Odoo modules'
    allow_config_file = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser.add_argument('modules', nargs='*', help=("Modules to install"))

    def run(self, cmdargs):
        parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)
        for db_name in tools.config['db_name']:
            with self.build_env(db_name, install_modules=parsed_args.modules):
                pass


class ModuleUpgrade(Subcommand):
    """ Upgrade Odoo modules """
    description = 'Upgrade Odoo modules'
    allow_config_file = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser.add_argument('modules', nargs='*', help=("Modules to upgrade"))

    def run(self, cmdargs):
        parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)
        for db_name in tools.config['db_name']:
            with self.build_env(db_name, update_module=True, upgrade_modules=parsed_args.modules):
                pass


class ModuleUninstall(Subcommand):
    """ Uninstall Odoo modules """

    description = 'Uninstall Odoo modules'
    allow_config_file = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser.add_argument('modules', nargs='*', help=("Modules to uninstall"))

    def run(self, cmdargs):
        parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)
        for db_name in tools.config['db_name']:
            with self.build_env(db_name) as env:
                env['ir.module.module'].sudo().search([('name', 'in', parsed_args.modules)]).module_uninstall()


class Module(Command):
    """ Install, Upgrade, Uninstall Odoo modules """
    subcommands = ModuleInstall, ModuleUpgrade, ModuleUninstall, ModuleDemo
