# -*- coding: utf-8 -*-
##############################################################################
#
#    ODOO Open Source Management Solution
#
#    ODOO Addon module by Sprintit Ltd
#    Copyright (C) 2018 Sprintit Ltd (<http://sprintit.fi>).
#
##############################################################################

from odoo import api, fields, models, _



def clean(reference):
    "Remove unwanted characters"
    allowed_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(i for i in str(reference) if i.upper() in allowed_chars)


def numeric(reference):
    "Numeric reprensation of the reference"
    return "".join(str(j) for i in str(reference) for j in ("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(i.upper()),) if j >= 0)


def is_valid_rf(reference):
    """Check if the number provided is a valid ISO 11649 structured creditor
    number. This checks the length, formatting and check digits."""
    reference = clean(reference)
    if len(reference) < 5 or len(reference) > 25:
        return False
    if not reference.startswith('RF'):
        return False
    num = numeric(reference[4:] + reference[0:4])
    return int(num) % 97 == 1

def rf_from_fi_reference(reference):
    """ Creates RF reference from finnish structured reference
    """
    reference = clean(reference)
    num = numeric(reference)
    check = "%02d" % (98 - int(num + "271500") % 97)
    return "RF" + check + reference

def format_rf_reference(reference):
    "Printable version of international RF reference"
    reference = clean(reference)
    return " ".join(reference[i:i+4] for i in range(0, len(reference), 4))


#  The following functions are created based on this document:
# https://www.finanssiala.fi/maksujenvalitys/dokumentit/Forming_a_Finnish_reference_number.pdf


def is_valid_fi(number):
    """Check if the number provided is a valid finnish structured creditor
    number. This checks the length, formatting and check digits."""

    try:
        reference = clean(number)
        return reference == add_check_digit(reference[:-1]) \
            and len(reference) <= 20 and len(reference) >= 4
    except ValueError:
        return False


def format_finnish_reference(reference):
    """ According to Finance Finland (FFI) recommendations
    the reference should be formatted into groups of five digits separated
    by a space."""

    # Reverse reference to start count from last number
    reversed_ref = reversed(reference)
    # Add space if index is dividable by 5
    parts = [c + (' ' if i and i % 5 == 0 else '') for i, c in enumerate(reversed_ref)]
    # Reverse the parts to return reference in original order
    return ''.join(reversed(parts))

def add_check_digit(body):
    """Adds check digit to finnish references calculated based on
    finnish standard for structured references"""

    body = clean(body)
    multipliers = (7, 3, 1)
    numbers_reversed = [int(char) for char in reversed(body)]
    # All digits of the reference number are multiplied from right to left with the values 7, 3, 1, 7, 3, 1...
    multiplied_sum = sum(multipliers[i % 3] * x for i, x in enumerate(numbers_reversed))
    # The sum is subtracted from the following full ten.
    # The resulting difference is the checksum, the final digit in the reference number.
    # If the difference is 10, the checksum is 0.
    check_digit = (10 - (multiplied_sum % 10)) % 10
    return body + str(check_digit)



class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # computed fields
    bank_reference_formatted = fields.Char(string='Bank Reference', compute='_bank_reference_formatted',
        help="Printable bank reference according to ​Finance Finland (FFI) recommendations")
 
    bank_payment_barcode = fields.Char(string='Bank Barcode', compute='_bank_payment_barcode')

    is_reference_duplicate = fields.Boolean('Duplicate vendor refenrence', compute='_compute_is_reference_duplicate',
        help="This field is used for alerting the user about duplicated vendor references")

    reference_type = fields.Selection(
        selection=[
            ('none', 'Free Reference'),
            ('fi_bank_reference', _('Finnish Bank Reference')),
            ('rf_bank_reference', _('International Bank Reference')),
        ],
        string='Reference Type',
        readonly=True,
        default='none',
        compute='_compute_reference_type',
        help="The type of the vendor reference. Structured references are handled differently when generating payment files.",
    )


    @api.one
    def _compute_is_reference_duplicate(self):
        if self.reference and self.type in ('in_invoice', 'in_refund') and self.company_id and self.commercial_partner_id:
            # Query made with sql to maintain performance with large amount of invoices
            sql = """\
                SELECT      id
                FROM        account_invoice
                WHERE       type = %s
                AND         reference = %s
                AND         company_id = %s
                AND         commercial_partner_id = %s
            """
            vals = [self.type, self.reference, self.company_id.id, self.commercial_partner_id.id]
            # If record is being edited its' id is an instance of odoo.models.NewId
            # and can't be used in query
            if isinstance(self.id, int):
                sql += "\nAND id != %s"
                vals.append(self.id)
        
            self._cr.execute(sql, vals)
            result = self._cr.fetchall()
            if result:
                self.is_reference_duplicate = True
                return
        self.is_reference_duplicate = False


    @api.multi
    def _check_duplicate_supplier_reference(self):
        # In Finland for example tax payments have the same reference number
        # during the same financial period. We can't raise an error, but instead
        # we will warn the customer if duplicates are detected
        pass


    @api.one
    @api.depends('reference', 'company_id.invoice_reference_type')
    def _bank_reference_formatted(self):
        """Generate printable reference for outgoing invoices"""
        if self.reference and self.type in ('out_invoice', 'out_refund'):
            ref_type = self.company_id.invoice_reference_type
            if ref_type == 'fi_bank_reference':
                self.bank_reference_formatted = format_finnish_reference(self.reference)
            elif ref_type == 'rf_bank_reference':
                self.bank_reference_formatted = format_rf_reference(self.reference)


    # bank barcode calculation based on standard
    @api.one
    @api.depends('date_due', 'amount_total', 'reference', 'partner_bank_id')
    def _bank_payment_barcode(self):
        # http://www.fkl.fi/teemasivut/sepa/tekninen_dokumentaatio/Dokumentit/Pankkiviivakoodi-opas.pdf
        barcode = ''
        partner_bank_id = self.partner_bank_id or self.company_id.bank_ids and self.company_id.bank_ids[0]
        if partner_bank_id and self.date_due:
            # barcode parts, formatted
            amount = "%06d%02d" % (int(self.amount_total), (self.amount_total - int(self.amount_total)) * 100)
            acc_number = partner_bank_id.acc_number[2:18]
            due_date = str(self.date_due).replace('-','')[2:8]
            # If self.reference isn't valid self.reference_type will be 'none'
            if self.reference_type == 'fi_bank_reference':
                reference = "%020d" % (int(self.reference))
                # full barcode, version 4
                barcode = "4%s%s000%s%s" % (acc_number, amount, reference, due_date)
            elif self.reference_type == 'rf_bank_reference':
                # barcode, version 5
                reference = self.reference.replace(' ', '')[2:]
                reference = "%02d%021d" % (int(reference[:2]), int(reference[2:]))
                barcode = "5%s%s%s%s" % (acc_number, amount, reference, due_date)
        self.bank_payment_barcode = barcode

    @api.one
    @api.depends('reference')
    def _compute_reference_type(self):
        """ If reference is set and it doesn't match ISO 11649 or finnish standard
        for structured references, this 'reference_type' field will be 'none' resulting in
        alert for user viewing the invoice."""
        if self.reference:
            if is_valid_fi(self.reference):
                self.reference_type = 'fi_bank_reference'
                return
            elif is_valid_rf(self.reference):
                self.reference_type = 'rf_bank_reference'
                return
        self.reference_type = 'none'


    @api.multi
    def _get_computed_reference(self):
        self.ensure_one()
        if self.company_id.invoice_reference_type == 'fi_bank_reference':
            reference_body = self.env['ir.sequence'].next_by_code('fi.bank.reference')
            return add_check_digit(reference_body)
        elif self.company_id.invoice_reference_type == 'rf_bank_reference':
            reference_body = self.env['ir.sequence'].next_by_code('fi.bank.reference')
            return rf_from_fi_reference(add_check_digit(reference_body))
        return super()._get_computed_reference()
