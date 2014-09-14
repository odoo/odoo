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
from openerp.exceptions import RedirectWarning
from openerp.tools.translate import _

# This class is intended to be present in sass, but not in master
class res_company(models.Model):
    _inherit = 'res.company'

    docsaway_can_try = fields.Boolean("Can try freely DocsAway", default=True) # Set False in master
    docsaway_counter = fields.Integer("Remaining free letters to send", default=0)


    @api.multi
    def _check_docsaway_try(self):
        """ Return the number of remaining free letters """
        for rec in self:
            if rec.docsaway_can_try:
                rec.docsaway_can_try = False
                rec.docsaway_counter = 10 # The number of letters we give
            return rec.docsaway_counter


    @api.multi
    def _get_credentials_docsaway_try(self):
        """ If the company can try the service, return the tuple email,
            installation_key, True
            Otherwise, return False, False, False
        """
        for rec in self:
            counter = rec._check_docsaway_try()
            if counter > 0:
                docsaway_email = "administrator@odoo.com"
                docsaway_installation_key = "76qF8iub0hX2dhOVtU55bo9X2l7jWp1FXHwt6UVh3MLbsliA0sNZ5GGoKyJ5hR0I"
                return docsaway_email, docsaway_installation_key, True
            # else
            return False, False, False
        
    
    @api.multi
    def _check_send_free_docsaway(self, count):
        for rec in self:
            counter = rec._check_docsaway_try()
            if counter - count < 0:
                action = self.env.ref('base_setup.action_general_configuration')
                msg = _("You don't have enough free mails to send.") + "\n" + \
                    _("Please open a new DocsAway account (follow instructions in General Settings -> Send Documents).")
                raise RedirectWarning(msg, action.id, _('Configure Account Now'))
                
    
    @api.multi
    def _send_free_docsaway(self, count):
        for rec in self:
            self._check_send_free_docsaway(count)
            self.docsaway_counter -= count
            
