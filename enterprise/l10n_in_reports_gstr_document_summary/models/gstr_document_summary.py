# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

DOCUMENT_TYPE_LIST = [
    ('1', '1 - Invoice for Outward Supply'),
    ('2', '2 - Invoice for Inward Supply from Unregistered Person'),
    ('3', '3 - Revised Invoice'),
    ('4', '4 - Debit Note'),
    ('5', '5 - Credit Note'),
    ('6', '6 - Receipt Voucher'),
    ('7', '7 - Payment Voucher'),
    ('8', '8 - Refund Voucher'),
    ('9', '9 - Delivery Challan for Job work'),
    ('10', '10 - Delivery Challan for Supply on Approval'),
    ('11', '11 - Delivery Challan in case of Supply of Liquid Gas'),
    ('12', '12 - Delivery Challan in cases other than by way of supply (excluding at S no. 9 to 11) '),
]


class GSTRDocumentSummaryLine(models.Model):
    _name = 'l10n_in.gstr.document.summary.line'
    _description = 'GSTR Document Summary Line'
    _order = 'nature_of_document asc'

    return_period_id = fields.Many2one('l10n_in.gst.return.period', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='return_period_id.company_id')
    nature_of_document = fields.Selection(DOCUMENT_TYPE_LIST, string='Nature of Document', required=True)
    serial_from = fields.Char(string="Sr. No. From", required=True)
    serial_to = fields.Char(string="Sr. No. To", required=True)
    total_issued = fields.Integer(string="Total Issued", compute='_compute_total_issued', readonly=False, store=True)
    total_cancelled = fields.Integer(string="Total Cancelled", required=True, default=0)
    net_issued = fields.Integer(string="Net Issued", compute='_compute_net_issued')

    _sql_constraints = [
        ('check_total_issued', 'CHECK(total_issued >= 0)', "Total issued cannot be negative."),
        ('check_total_cancelled', 'CHECK(total_cancelled >= 0)', "Total cancelled cannot be negative."),
        ('check_cancel_below_issued', 'CHECK(total_cancelled <= total_issued)', "Total cancelled cannot exceed total issued."),
    ]

    @api.constrains('serial_from', 'serial_to')
    def _check_serial(self):
        serial_pattern = re.compile(r"^(?=.{1,16}$)([\/\\\-0]*[a-zA-Z0-9\/\\\-]*[a-zA-Z1-9]+[a-zA-Z0-9\/\\\-]*)$")
        for record in self:
            field_pairs = [
                ('serial_from', record.serial_from, 'Sr. No. From'),
                ('serial_to', record.serial_to, 'Sr. No. To'),
            ]
            for field_name, value, label in field_pairs:
                if not value:
                    continue
                if not serial_pattern.match(value):
                    raise ValidationError(
                        _("Invalid format for '%s'. It must be between 1-16 characters, it can contain only letters, digits, '/', '\\', -, and should have at least one non-zero letter or digit.", label
                    ))
                domain = [
                    ('id', '!=', record.id), ('return_period_id', '=', record.return_period_id.id),
                    '|',
                    ('serial_from', '=', value), ('serial_to', '=', value)
                ]
                if self.search_count(domain):
                    raise ValidationError(
                        _("Duplicate value found '%s'. Serial numbers should be unique.", value)
                    )

    @api.depends('serial_from', 'serial_to')
    def _compute_total_issued(self):
        for record in self:
            record.total_issued = 0
            if record.serial_from and record.serial_to:
                from_match = re.search(r'\d+$', record.serial_from or '')
                to_match = re.search(r'\d+$', record.serial_to or '')
                if from_match and to_match:
                    from_num = int(from_match.group())
                    to_num = int(to_match.group())
                    record.total_issued = max(0, to_num - from_num + 1)

    @api.depends('total_issued', 'total_cancelled')
    def _compute_net_issued(self):
        for record in self:
            record.net_issued = record.total_issued - record.total_cancelled
