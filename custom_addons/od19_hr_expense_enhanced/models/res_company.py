# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ------------------------------------------------------------------
    # Per-diem policy - Section 42(3) Revenue Code (เบี้ยเลี้ยง ม.42(3))
    # ------------------------------------------------------------------
    od19_per_diem_rate_domestic = fields.Monetary(
        string='Per Diem Standard Rate / Day (Domestic) / วงเงินเบี้ยเลี้ยงต่อวัน (ในประเทศ)',
        currency_field='currency_id',
        help='Standard exempt per-diem rate per day for domestic travel, '
             'used as the limit when validating a per-diem allowance.',
    )
    od19_per_diem_rate_overseas = fields.Monetary(
        string='Per Diem Standard Rate / Day (Overseas) / วงเงินเบี้ยเลี้ยงต่อวัน (ต่างประเทศ)',
        currency_field='currency_id',
        help='Standard exempt per-diem rate per day for overseas travel, '
             'used as the limit when validating a per-diem allowance.',
    )

    def _od19_per_diem_rate(self, region):
        """Return the standard per-diem rate per day for the given region."""
        self.ensure_one()
        if region == 'overseas':
            return self.od19_per_diem_rate_overseas
        return self.od19_per_diem_rate_domestic
