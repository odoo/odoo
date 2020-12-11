# -*- coding: utf-8 -*-

from odoo import models, fields


class PosDownloadDsfinvkExport(models.TransientModel):
    _name = 'pos.download_dsfinvk_export_wizard'
    file_name = fields.Char(readonly=True)
    file = fields.Binary(readonly=True)

