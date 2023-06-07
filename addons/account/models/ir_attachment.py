# -*- coding: utf-8 -*-
from odoo import models, api

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    # -------------------------------------------------------------------------
    # XSD validation
    # -------------------------------------------------------------------------

    @api.model
    def action_download_xsd_files(self):
        # To be extended by localisations, where they can download their necessary XSD files
        # Note: they should always return super().action_download_xsd_files()
        return
