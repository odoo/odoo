# Copyright 2020 Camptocamp
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import fields, models


class IrModelFields(models.Model):
    _inherit = "ir.model.fields"

    ttype = fields.Selection(
        selection_add=[("job_serialized", "Job Serialized")],
        ondelete={"job_serialized": "cascade"},
    )
