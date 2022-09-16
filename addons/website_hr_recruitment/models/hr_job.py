# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Job(models.Model):
    _inherit = "hr.job"

    job_details = fields.Html('Process Details',
        help="Complementary information that will appear on the job submission page",
        default="""
            <div class="d-flex flex-column align-items-baseline">
                <span class="text-muted small">Time to Answer</span>
                <h6>2 open days</h6>
            </div>
            <div class="d-flex flex-column align-items-baseline">
                <span class="text-muted small">Process</span>
                <h6>1 Phone Call</h6>
                <h6>1 Onsite Interview</h6>
            </div>
            <div class="d-flex flex-column align-items-baseline">
                <span class="text-muted small">Days to get an Offer</span>
                <h6>4 Days after Interview</h6>
            </div>
        """)
