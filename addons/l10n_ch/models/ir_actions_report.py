# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from pathlib import Path
from reportlab.graphics.shapes  import Image as ReportLabImage
from reportlab.lib.units import mm

CH_QR_CROSS_SIZE_RATIO = 0.1214 # Ratio between the side length of the Swiss QR-code cross image and the QR-code's
CH_QR_CROSS_FILE = Path('../static/src/img/CH-Cross_7mm.png') # Image file containing the Swiss QR-code cross to add on top of the QR-code

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def get_available_barcode_masks(self):
        rslt = super(IrActionsReport, self).get_available_barcode_masks()
        rslt['ch_cross'] = self.apply_qr_code_ch_cross_mask
        return rslt

    @api.model
    def apply_qr_code_ch_cross_mask(self, width, height, barcode_drawing):
        cross_width = CH_QR_CROSS_SIZE_RATIO * width
        cross_height = CH_QR_CROSS_SIZE_RATIO * height
        cross_path = Path(__file__).absolute().parent / CH_QR_CROSS_FILE
        qr_cross = ReportLabImage((width/2 - cross_width/2) / mm, (height/2 - cross_height/2) / mm, cross_width / mm, cross_height / mm, cross_path.as_posix())
        barcode_drawing.add(qr_cross)
