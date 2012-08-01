# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2012 OpenERP S.A. (<http://openerp.com>).
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

import re
from openerp.osv import fields, osv
from tools.translate import _


class mail_alias(osv.Model):
    """A Mail Alias is a mapping of an email address with a given OpenERP Document
       model. It is used by OpenERP's mail gateway when processing incoming emails
       sent to the system. If the recipient address (To) of the message matches
       a Mail Alias, the message will be either processed following the rules
       of that alias. If the message is a reply it will be attached to the
       existing discussion on the corresponding record, otherwise a new
       record of the corresponding model will be created.
       
       This is meant to be used in combination with a catch-all email configuration
       on the company's mail server, so that as soon as a new mail.alias is
       created, it becomes immediately usable and OpenERP will accept email for it.
     """
    _name = 'mail.alias'
    _description = "Mail Alias"
    _rec_name = 'alias_name'

    def _get_alias_domain(self, cr, uid, ids, name, args, context=None):
        res = {}
        config_parameter_pool = self.pool.get("ir.config_parameter")
        domain = config_parameter_pool.get_param(cr, uid, "mail.catchall.domain", context=context)   
        for alias in self.browse(cr, uid, ids, context=context):
            res[alias.id] = domain or ""
        return res

    _columns = {
        'alias_name': fields.char('Mailbox Alias', size=255, required=True,
                            help="The name of the mailbox alias, e.g. 'jobs' "
                                 "if you want to catch emails for <jobs@example.my.openerp.com>",),
        'alias_model_id': fields.many2one('ir.model', 'Aliased Model', required=True,
                                          help="The model (OpenERP Document Kind) to which this alias "
                                               "corresponds. Any incoming email that does not reply to an "
                                               "existing record will cause the creation of a new record "
                                               "of this model (e.g. a Project Task)",
                                          # only allow selecting mail_thread models!
                                          #TODO kept doamin temporarily in comment, need to redefine domain
                                          #domain="[('field_id', 'in', 'message_ids')]"
                                          ),
        'alias_user_id': fields.many2one('res.users', 'Owner',
                                           help="The owner of records created upon receiving emails on this alias. "
                                                "If this field is kept empty the system will attempt to find the right owner "
                                                "based on the sender (From) address, or will use the Administrator account "
                                                "if no system user is found for that address."),
        'alias_defaults': fields.text('Default Values', required=True,
                                      help="The representation of a Python dictionary that will be evaluated to provide "
                                           "default values when creating new records."),
        'alias_force_thread_id': fields.integer('Record Thread ID',
                                      help="Optional ID of the thread (record) to which all "
                                           "messages will be attached, even if they did not reply to it. "
                                           "If set, this will disable the creation of new records completely."),
        'alias_domain': fields.function(_get_alias_domain, string="Alias Doamin", type='char', size=None),
    }

    _defaults = {
        'alias_defaults': '{}',
        'alias_user_id': lambda self,cr,uid, context: uid
    }

    _sql_constraints = [
        ('mailbox_uniq', 'UNIQUE(alias_name)', 'Unfortunately this mail alias is already used, please choose a unique one')
    ]

    def _check_alias_defaults(self, cr, uid, ids, context=None):
        """
        Strick constraints checking for the alias defaults values.
        it must follow the python dict format. So message_catachall
        will not face any issue.
        """
        for record in self.browse(cr, uid, ids, context=context):
            try:
                dict(eval(record.alias_defaults))
            except Exception:
                return False
        return True

    _constraints = [
        (_check_alias_defaults, '''Invalid expression, it must be a literal python dictionary definition e.g. "{'field': 'value'}"''', ['alias_defaults']),
    ]

    def name_get(self, cr, uid, ids, context=None):
        """
        Return the mail alias display alias_name, inclusing the Implicit and dynamic
        Email Alias Domain from config.
        e.g. `jobs@openerp.my.openerp.com` or `sales@openerp.my.openerp.com`
        """
        res = []
        for record in self.read(cr, uid, ids, ['alias_name', 'alias_domain'], context=context):
            domain_alias = "%s@%s"%(record['alias_name'], record['alias_domain'])
            res.append((record['id'], domain_alias))
        return res

    def _generate_alias(self, cr, uid, name, sequence=1 ,context=None):
        """
        If alias is existing then this method will create a new unique alias name
        by appending n sequence integer number.
        """
        new_name = "%s%s"%(name, sequence)
        search_alias = self.search(cr, uid, [('alias_name', '=', new_name)])
        if search_alias:    
            new_name = self._generate_alias(cr, uid, name, sequence+1 ,context=None)
            if not self.search(cr, uid, [('alias_name', '=', new_name)]):
                return new_name
        else:
            return new_name

    def create_unique_alias(self, cr, uid, vals, context=None):
        """
        Methods accepts the vals param in dict format and create new alias record
        @vals : dict accept {alias_name: '', alias_model_id: '',...}
        @return int: New alias_id
        """
        model_pool = self.pool.get('ir.model')
        alias_name = re.sub(r'\W+', '_', vals['alias_name']).lower()
        values = {'alias_name': alias_name}
        #Find for the mail alias exist or not if exit then get new mail address.
        saids = self.search(cr, uid, [('alias_name', '=',alias_name)])
        if saids:
            alias_name = self._generate_alias(cr, uid, alias_name, sequence=1, context=context)
        values.update({'alias_name': alias_name})
        #Set the model fo rhte mail alias
        model_sids = model_pool.search(cr, uid, [('model', '=', vals['alias_model_id'])])
        values.update({'alias_model_id': model_sids[0]})
        return self.create(cr, uid, values, context=context)


