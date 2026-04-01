# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import SQL


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def init(self):
        if self.env.registry.has_trigram:
            indexed_field = SQL('UNACCENT(index_content)') if self.env.registry.has_unaccent else SQL('index_content')

            self.env.cr.execute(SQL('''
                CREATE INDEX IF NOT EXISTS ir_attachment_index_content_applicant_trgm_idx
                    ON ir_attachment USING gin (%(indexed_field)s gin_trgm_ops)
                 WHERE res_model = 'hr.applicant'
            ''', indexed_field=indexed_field))
