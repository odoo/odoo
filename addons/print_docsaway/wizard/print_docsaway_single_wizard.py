# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2014 OpenERP SA (<https://www.odoo.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api, fields, models


class ConfirmDeliverySingleWizard(models.TransientModel):
    _name = 'print_docsaway.single_wizard'
    _rec_name = 'pdf'

    wizard_id = fields.Many2one('print_docsaway.multiple_wizard', "Wizard", default=False)
    wizard_customer_id = fields.Many2one('print_docsaway.customer_wizard', "Wizard", default=False)
    mail_id = fields.Many2one('print.docsaway', "Mail")
    no_multiple_wizard = fields.Boolean("No Multiple Wizard", default=False)

    free_count = fields.Integer("Remaining Free Letters", related='mail_id.free_count')
    price = fields.Float("Cost to Deliver", related='mail_id.price', digits=(16,2))
    balance = fields.Float("Current DocsAway Balance", related='mail_id.balance', digits=(16,2))
    remaining = fields.Float("Remaining DocsAway Balance", related='mail_id.remaining', digits=(16,2))
    station = fields.Char("Station ID", related='mail_id.station')
    courier = fields.Char("Courier ID", related='mail_id.courier')
    nb_pages = fields.Integer("Number of Pages", related='mail_id.nb_pages')
    partner_id = fields.Many2one('res.partner', string='Address', related='mail_id.partner_id')
    pdf = fields.Binary("Report PDF", related='mail_id.pdf')
    ink = fields.Selection([('BW', 'Black & White'),('CL', 'Colour')], "Ink", related='mail_id.ink')
    already_sent = fields.Boolean('Already Sent', related='mail_id.already_sent')
    sent_date = fields.Datetime('Sent Date', related='mail_id.sent_date')
    src_id = fields.Integer('Source ID', related='mail_id.src_id')
    model_name = fields.Char('Model Name', related='mail_id.model_name')
    currency_id = fields.Many2one('res.currency', string='Currency',
         related='mail_id.currency_id', readonly=True, track_visibility='always')
    first_call = fields.Boolean('First Call', default=True)
    address_valid = fields.Boolean('Valid Address', related='mail_id.address_valid')


    @api.multi
    def action_send_mail(self):
        for rec in self:
            rec.mail_id._send_mail()
            if rec.model_name is not "":
                self.env[rec.model_name]._set_as_sent(rec.src_id)
            rec.unlink()
        return {'type': 'ir.actions.act_window_close'}


    @api.onchange('ink')
    def _on_change_ink(self):
        for rec in self:
            # Because in the onchange method, assigned values are not written to
            # database but only returned to the client, we must enforce a
            # record update in the database to keep the changes

            # Avoid to redo already done computation
            if not rec.first_call:
                rec.mail_id.ink = rec.ink
                rec.mail_id._compute_price(rec.balance)
                rec.mail_id.write({
                    'price': rec.price,
                    'courier': rec.courier,
                    'station': rec.station,
                    'ink': rec.ink,
                    'remaining': rec.remaining,
                })
            rec.first_call = False


    @api.multi
    def default_get(self):
        for rec in self:
            if 'docsaway_mail_id' in rec._context:
                return {
                    'mail_id': rec._context['docsaway_mail_id'],
                    'no_multiple_wizard': True,
                    'first_call': True,
                }
