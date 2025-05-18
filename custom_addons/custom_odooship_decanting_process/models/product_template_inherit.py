from odoo import models, api, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.onchange('default_code')
    def _onchange_default_code(self):
        if not self.default_code:
            return

        # Build domain to check for same default_code and same tenant_id
        domain = [('default_code', '=', self.default_code)]
        if self.id:
            domain.append(('id', '!=', self.id))
        if self.tenant_id:
            domain.append(('tenant_id', '=', self.tenant_id.id))

        # Search in product.template for duplicates in the same tenant
        if self.env['product.template'].search(domain, limit=1):
            return {
                'warning': {
                    'title': _("Note:"),
                    'message': _("The Internal Reference '%s' already exists for this tenant." % self.default_code),
                }
            }
