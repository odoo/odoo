# Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class DocumentKnowledgeConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_ir_attachment_user = fields.Boolean(
        string="Central access to Documents",
        implied_group="document_knowledge.group_ir_attachment_user",
    )
