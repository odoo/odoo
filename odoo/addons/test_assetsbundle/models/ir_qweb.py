from odoo import models

class IrQweb(models.AbstractModel):
    _inherit = 'ir.qweb'

    def _register_hook(self):
        super()._register_hook()
        # if this module is installed, we are in a test environement.
        # pregenerate assets at the end of the loading to speedup tests
        registry = self.env.registry
        if registry.updated_modules and not registry.ready:
            self._pregenerate_assets_bundles()
