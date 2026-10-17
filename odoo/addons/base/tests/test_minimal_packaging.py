import logging

from odoo.tests import TransactionCase, tagged

_logger = logging.getLogger(__name__)


class PackagingTestException(Exception):
    pass


@tagged('-standard', '-at_install', 'postinstall', 'packaging')
class Packaging(TransactionCase):

    def test_minimal_after_packaging(self):

        installed_modules = self.env["ir.module.module"].search([
            ("state", "=", "installed"),
        ])

        modules_to_install = self.env["ir.module.module"].search([
            ("state", "=", "to_install"),
        ])
        if modules_to_install:
            msg = "Package test: FAILED. Not able to install dependencies of base."
            _logger.error(msg)
            raise PackagingTestException(msg)

        nb_installed = len(installed_modules)
        _logger.info("Package test: successfuly installed %s modules", nb_installed)
