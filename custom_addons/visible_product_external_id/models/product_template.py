from odoo import api, fields, models


def _define_external_id_field():
    """Define the field to display all external IDs as a comma-separated string"""
    return fields.Char(
        string='External ID(s)',
        compute='_compute_external_id',
        help="All external IDs as comma-separated string",
        readonly=True,
        store=False
    )


def _set_external_id(mdl):
    """Format all external IDs as a comma-separated string"""
    
    all_external_ids = mdl.env['ir.model.data'].search([
        ('model', '=', mdl._name),
        ('res_id', 'in', mdl.ids)
    ])
    
    record_to_external_ids = {}
    for ext_id in all_external_ids:
        if ext_id.res_id not in record_to_external_ids:
            record_to_external_ids[ext_id.res_id] = []
        record_to_external_ids[ext_id.res_id].append(ext_id)
    
    for record in mdl:
        ext_ids = record_to_external_ids.get(record.id, [])
        if ext_ids:
            ext_id_list = [f"{ext_id.module}.{ext_id.name}" for ext_id in ext_ids]
            record.external_id = ", ".join(ext_id_list)
        else:
            record.external_id = False


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    external_id = _define_external_id_field()

    @api.depends()
    def _compute_external_id(self):
        _set_external_id(self)


class ProductProduct(models.Model):
    _inherit = 'product.product'
    external_id = _define_external_id_field()

    @api.depends()
    def _compute_external_id(self):
        _set_external_id(self) 