# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

from odoo import models, fields


class TnpdPrisonMaster(models.Model):
    _name = 'tnpd.prison.master'
    _description = 'Prison / Jail Master'
    _rec_name = 'name'
    _order = 'prison_type, name'

    name = fields.Char(string='Name', required=True)
    prison_type = fields.Selection(
        selection=[
            ('central', 'Central Prison'),
            ('district', 'District Jail'),
            ('sub', 'Sub Jail'),
        ],
        string='Type',
        required=True,
        index=True,
    )
    active = fields.Boolean(default=True)

    _uniq_name_type = models.Constraint(
        'UNIQUE (name, prison_type)',
        'A prison/jail with this name already exists for the selected type.',
    )
