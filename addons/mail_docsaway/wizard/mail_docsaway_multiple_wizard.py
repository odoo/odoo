# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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


class ConfirmDeliveryMultipleWizard(models.TransientModel):
    _name = 'mail_docsaway.multiple_wizard'
    _rec_name = 'remaining'
    
    
    @api.model
    def _default_currency(self):
        return self.env['mail_docsaway.api']._get_currency()
        
    
    @api.model
    def _default_ink(self):
        return self.env['mail_docsaway.api']._get_ink()
        
        
    @api.model
    def _default_free_count(self):
        return self.env['mail_docsaway.api']._get_free_count()
    

    price = fields.Float('Cost to Deliver', compute='_compute_price', digits=(16,2))
    balance = fields.Float('Current DocsAway Balance', compute='_compute_price', digits=(16,2))
    remaining = fields.Float('Remaining DocsAway Balance', compute='_compute_price', digits=(16,2))
    ink = fields.Selection([('BW', 'Black & White'),('CL', 'Colour')], 'Ink', required=True, default=_default_ink)
    require_attention = fields.Boolean("Invalid Address", compute='_compute_require_attention')
    currency_id = fields.Many2one('res.currency', string='Currency',
        required=True, readonly=True, default=_default_currency, track_visibility='always')
    free_count = fields.Integer("Remaining Free Letters", default=_default_free_count)
    count_valid_mails = fields.Integer("Valid Mails", compute='_compute_valid_mails')
    wiz_ids = fields.One2many('mail_docsaway.single_wizard', 'wizard_id', string='Mails')


    @api.multi
    def action_send_mails(self):
        # First check if free mail, and if not overtake it
        dummy1, dummy2, sass_account = self.env['mail_docsaway.api']._get_credentials()
        if sass_account:
            company_id = self.env.user.company_id
            company_id._check_send_free_docsaway(self.count_valid_mails)
            
        for rec in self:
            for mail in rec.wiz_ids:
                sent = mail.mail_id._send_mail_multiple()
                if mail.mail_id.model_name and sent:
                    self.env[mail.mail_id.model_name]._set_as_sent(mail.mail_id.src_id)
                mail.mail_id.unlink()
        return {'type': 'ir.actions.act_window_close'}


    @api.onchange('ink')
    def _on_change_ink(self):
        # Creating the wiz_ids now allow to show an "well formed" wizard with
        # empty list instead of a pure blank wizard
        wiz_id = self.id
        my_wiz_ids = self.env['mail_docsaway.single_wizard'].search([('wizard_id','=',wiz_id)])
        if len(my_wiz_ids) == 0:
            model_name = self._context.get('active_model', None)
            report_model = self._context.get('report_model', None)
            active_ids = self._context.get('active_ids', [])
            self.wiz_ids = self.env['mail_docsaway.api']._prepare_multiple_deliveries(active_ids, model_name, report_model, wiz_id, ink=self.ink)
        else:
            self.wiz_ids = my_wiz_ids
            for wiz in self.wiz_ids:
                wiz.mail_id.ink = self.ink
            
    
    @api.one
    @api.depends('wiz_ids')
    def _compute_require_attention(self):
        for mail in self.wiz_ids:
            if mail.partner_id and (mail.already_sent or not mail.address_valid):
                self.require_attention = True
                return
        self.require_attention = False
    
    
    @api.one
    @api.depends('ink', 'wiz_ids')
    def _compute_price(self):
        if self.wiz_ids:
            self.price = sum(mail.price for mail in self.wiz_ids)
            self.balance = self.wiz_ids[-1].balance
            self.remaining = self.balance - self.price
        else:
            self.price = 0.0
            self.balance = 0.0
            self.remaining = 0.0
        
    @api.one
    @api.depends('wiz_ids')
    def _compute_valid_mails(self):
        valid = 0
        for mail in self.wiz_ids:
            if mail.nb_pages > 0:
                valid += 1
        self.count_valid_mails = valid
