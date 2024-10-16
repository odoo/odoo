from odoo import models
from odoo.tools import config
from odoo.addons import base
init = config['init']


class IrQweb(base.IrQweb):

    def _register_hook(self):
        super()._register_hook()
        # if this module is installed, we are in a test environement, this is
        # especially true on runbot where all modules are installed.
        # pregenerate assets at the end of the loading to speedup tests
        registry = self.env.registry
        if init and registry.updated_modules and not registry.ready:
            self._pregenerate_assets_bundles()
