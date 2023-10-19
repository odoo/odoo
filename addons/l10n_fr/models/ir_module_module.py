from odoo import models


class IrModuleModule(models.Model):
    _name = "ir.module.module"
    _description = 'Module'
    _inherit = _name

    # The following override allows for the company registry to be translated to "SIREN" whenever the translation occurs
    # in a French localization.
    # Overriding the .po in this case wouldn't be sufficient since the French translation would override the base one,
    # hence overriding every other French translation.
    # A later refactor of the main _load_module_terms method might make this override unnecessary.
    def _load_module_terms(self, modules, langs, overwrite=False):
        res = super()._load_module_terms(modules, langs, overwrite=overwrite)

        if langs and langs == ['fr_FR'] and self.env.company.country_code == 'FR':
            self.env.ref('base.field_res_company__company_registry').with_context(lang='fr_FR').field_description = 'SIREN'
        return res
