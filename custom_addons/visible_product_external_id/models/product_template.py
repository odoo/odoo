from odoo import api, fields, models


class ExternalIdMixin(models.AbstractModel):
    """Mixin to add external ID functionality to models."""
    _name = 'external.id.mixin'
    _description = 'External ID Mixin'

    external_id = fields.Char(
        string='External ID(s)',
        compute='_compute_external_id',
        help="All external IDs as comma-separated string",
        readonly=True,
        store=False,
        search='_search_external_id'
    )

    @api.depends()
    def _compute_external_id(self):
        """Compute the external ID field for the record."""
        all_external_ids = self.env['ir.model.data'].search([
            ('model', '=', self._name),
            ('res_id', 'in', self.ids)
        ])
        
        record_to_external_ids = {}
        for ext_id in all_external_ids:
            if ext_id.res_id not in record_to_external_ids:
                record_to_external_ids[ext_id.res_id] = []
            record_to_external_ids[ext_id.res_id].append(ext_id)
        
        for record in self:
            ext_ids = record_to_external_ids.get(record.id, [])
            if ext_ids:
                ext_id_list = [f"{ext_id.module}.{ext_id.name}" for ext_id in ext_ids]
                record.external_id = ", ".join(ext_id_list)
            else:
                record.external_id = False

    @api.model
    def _search_external_id(self, operator, value):
        """Search for records by their external ID."""
        if not value:
            return []
        
        domain = [
            ('model', '=', self._name),
            '|',
            ('name', 'ilike', value),
            ('module', 'ilike', value)
        ]
        external_ids = self.env['ir.model.data'].search(domain)
        
        if not external_ids:
            return [('id', '=', False)]
            
        return [('id', 'in', external_ids.mapped('res_id'))]


class ProductTemplate(models.Model):
    _inherit = ['product.template', 'external.id.mixin']
    _name = 'product.template'


class ProductProduct(models.Model):
    _inherit = ['product.product', 'external.id.mixin']
    _name = 'product.product'