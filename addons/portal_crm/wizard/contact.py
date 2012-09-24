# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP S.A (<http://www.openerp.com>).
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

from openerp.osv import osv, fields
from openerp import SUPERUSER_ID

class crm_contact_us(osv.TransientModel):
    """ Create new leads through the "contact us" form """
    _name = 'portal_crm.crm_contact_us'
    _description = 'Contact form for the portal'
    _inherit = 'crm.lead'
    _columns = {
        'company_ids' : fields.many2many('res.company', string='Companies', readonly=True),
    }

    def _get_companies(self, cr, uid, context=None):
        """
        Fetch companies in order to display them in the wizard view

        @return a list of ids of the companies
        """
        r = self.pool.get('res.company').search(cr, uid, [], context=context)
        return r

    def _get_current_user_email(self, cr, uid, context=None):
        """
        If the user is logged in (i.e. not anonymous), get the user's email to
        pre-fill the email_from field.

        @return current user's email if the user isn't "anonymous", None otherwise
        """
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)

        if (user.login != 'anonymous'):
            return user.email
        else:
            return None

    _defaults = {
        'email_from' : _get_current_user_email,
        'company_ids' : _get_companies,
    }

    def create(self, cr, uid, values, context=None):
        """
        Since they potentially sensitive, we don't want any user to be able to
        read datas generated through this module.  That's why we'll write those
        information in the crm.lead table and leave blank entries in the
        portal_crm.crm_contact_us table.  This is why the create() method is
        overwritten.
        """
        crm_lead = self.pool.get('crm.lead')

        """
        Because of the complex inheritance of the crm.lead model and the other
        models implied (like mail.thread, among others, that performs a read
        when its create() method is called (in method message_get_subscribers()),
        it is quite complicated to set proper rights for this object.
        Therefore, user SUPERUSER_ID will perform the creation until a better
        workaround is figured out.
        """
        values['contact_name'] = values['name']
        crm_lead.create(cr, SUPERUSER_ID, dict(values,user_id=False), context)

        """
        Create an empty record in the portal_crm.crm_contact_us table.
        Since the 'name' field is mandatory, give an empty string to avoid an integrity error.
        """
        return super(crm_contact_us, self).create(cr, uid, {'name': ' '})

    def submit(self, cr, uid, ids, context=None):
        """ When the form is submitted, redirect the user to a "Thanks" message """
        return {'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': self._name,
                'res_id': ids[0],
                'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'portal_crm', 'wizard_contact_form_view_thanks')[1],
                'target': 'inline'
               }
