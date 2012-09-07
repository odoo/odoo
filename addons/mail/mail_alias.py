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

import logging
import re
import unicodedata

from openerp.osv import fields, osv
from openerp.tools import ustr
from openerp.modules.registry import RegistryManager
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)

# Inspired by http://stackoverflow.com/questions/517923
def remove_accents(input_str):
    """Suboptimal-but-better-than-nothing way to replace accented
    latin letters by an ASCII equivalent. Will obviously change the
    meaning of input_str and work only for some cases"""
    input_str = ustr(input_str)
    nkfd_form = unicodedata.normalize('NFKD', input_str)
    return u''.join([c for c in nkfd_form if not unicodedata.combining(c)])

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
    _description = "Email Aliases"
    _rec_name = 'alias_name'
    _order = 'alias_model_id, alias_name'

    def _get_alias_domain(self, cr, uid, ids, name, args, context=None):
        ir_config_parameter = self.pool.get("ir.config_parameter")
        domain = ir_config_parameter.get_param(cr, uid, "mail.catchall.domain", context=context)   
        return dict.fromkeys(ids, domain or "")

    _columns = {
        'alias_name': fields.char('Alias', required=True,
                            help="The name of the email alias, e.g. 'jobs' "
                                 "if you want to catch emails for <jobs@example.my.openerp.com>",),
        'alias_model_id': fields.many2one('ir.model', 'Aliased Model', required=True,
                                          help="The model (OpenERP Document Kind) to which this alias "
                                               "corresponds. Any incoming email that does not reply to an "
                                               "existing record will cause the creation of a new record "
                                               "of this model (e.g. a Project Task)",
                                          # hack to only allow selecting mail_thread models (we might
                                          # (have a few false positives, though)
                                          domain="[('field_id.name', '=', 'message_ids')]"),
        'alias_user_id': fields.many2one('res.users', 'Owner',
                                           help="The owner of records created upon receiving emails on this alias. "
                                                "If this field is not set the system will attempt to find the right owner "
                                                "based on the sender (From) address, or will use the Administrator account "
                                                "if no system user is found for that address."),
        'alias_defaults': fields.text('Default Values', required=True,
                                      help="A Python dictionary that will be evaluated to provide "
                                           "default values when creating new records for this alias."),
        'alias_force_thread_id': fields.integer('Record Thread ID',
                                      help="Optional ID of a thread (record) to which all incoming "
                                           "messages will be attached, even if they did not reply to it. "
                                           "If set, this will disable the creation of new records completely."),
        'alias_domain': fields.function(_get_alias_domain, string="Alias Domain", type='char', size=None),
    }

    _defaults = {
        'alias_defaults': '{}',
        'alias_user_id': lambda self,cr,uid,context: uid,
        # looks better when creating new aliases - even if the field is informative only
        'alias_domain': lambda self,cr,uid,context: self._get_alias_domain(cr, SUPERUSER_ID,[1],None,None)[1]
    }

    _sql_constraints = [
        ('alias_unique', 'UNIQUE(alias_name)', 'Unfortunately this email alias is already used, please choose a unique one')
    ]

    def _check_alias_defaults(self, cr, uid, ids, context=None):
        try:
            for record in self.browse(cr, uid, ids, context=context):
                dict(eval(record.alias_defaults))
        except Exception:
            return False
        return True

    _constraints = [
        (_check_alias_defaults, '''Invalid expression, it must be a literal python dictionary definition e.g. "{'field': 'value'}"''', ['alias_defaults']),
    ]

    def name_get(self, cr, uid, ids, context=None):
        """Return the mail alias display alias_name, inclusing the implicit
           mail catchall domain from config.
           e.g. `jobs@openerp.my.openerp.com` or `sales@openerp.my.openerp.com`
        """
        return [(record['id'], "%s@%s" % (record['alias_name'], record['alias_domain']))
                    for record in self.read(cr, uid, ids, ['alias_name', 'alias_domain'], context=context)]

    def _find_unique(self, cr, uid, name, context=None):
        """Find a unique alias name similar to ``name``. If ``name`` is
           already taken, make a variant by adding an integer suffix until
           an unused alias is found.
        """
        sequence = None
        while True:
            new_name = "%s%s" % (name, sequence) if sequence is not None else name
            if not self.search(cr, uid, [('alias_name', '=', new_name)]):
                break
            sequence = (sequence + 1) if sequence else 2
        return new_name

    def migrate_to_alias(self, cr, child_model_name, child_table_name, child_model_auto_init_fct,
        alias_id_column, alias_key, alias_prefix = '', alias_force_key = '', alias_defaults = {}, context=None):
        """ Installation hook to create aliases for all users and avoid constraint errors.

            :param child_model_name: model name of the child class (i.e. res.users)
            :param child_table_name: table name of the child class (i.e. res_users)
            :param child_model_auto_init_fct: pointer to the _auto_init function
                (i.e. super(res_users,self)._auto_init(cr, context=context))
            :param alias_id_column: alias_id column (i.e. self._columns['alias_id'])
            :param alias_key: name of the column used for the unique name (i.e. 'login')
            :param alias_prefix: prefix for the unique name (i.e. 'jobs' + ...)
            :param alias_force_key': name of the column for force_thread_id;
                if empty string, not taken into account
            :param alias_defaults: dict, keys = mail.alias columns, values = child
                model column name used for default values (i.e. {'job_id': 'id'})
        """

        # disable the unique alias_id not null constraint, to avoid spurious warning during 
        # super.auto_init. We'll reinstall it afterwards.
        alias_id_column.required = False

        # call _auto_init
        child_model_auto_init_fct(cr, context=context)

        registry = RegistryManager.get(cr.dbname)
        mail_alias = registry.get('mail.alias')
        child_class_model = registry.get(child_model_name)
        no_alias_ids = child_class_model.search(cr, SUPERUSER_ID, [('alias_id', '=', False)], context={'active_test':False})
        # Use read() not browse(), to avoid prefetching uninitialized inherited fields
        for obj_data in child_class_model.read(cr, SUPERUSER_ID, no_alias_ids, [alias_key]):
            alias_vals = {'alias_name': '%s%s' % (alias_prefix, obj_data[alias_key]) }
            if alias_force_key:
                alias_vals['alias_force_thread_id'] = obj_data[alias_force_key]
            alias_vals['alias_defaults'] = dict( (k, obj_data[v]) for k, v in alias_defaults.iteritems())
            alias_id = mail_alias.create_unique_alias(cr, SUPERUSER_ID, alias_vals, model_name=child_model_name)
            child_class_model.write(cr, SUPERUSER_ID, obj_data['id'], {'alias_id': alias_id})
            _logger.info('Mail alias created for %s %s (uid %s)', child_model_name, obj_data[alias_key], obj_data['id'])

        # Finally attempt to reinstate the missing constraint
        try:
            cr.execute('ALTER TABLE %s ALTER COLUMN alias_id SET NOT NULL' % (child_table_name))
        except Exception:
            _logger.warning("Table '%s': unable to set a NOT NULL constraint on column '%s' !\n"\
                            "If you want to have it, you should update the records and execute manually:\n"\
                            "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL",
                            child_table_name, 'alias_id', child_table_name, 'alias_id')

        # set back the unique alias_id constraint
        alias_id_column.required = True

    def create_unique_alias(self, cr, uid, vals, model_name=None, context=None):
        """Creates an email.alias record according to the values provided in ``vals``,
        with 2 alterations: the ``alias_name`` value may be suffixed in order to
        make it unique, and the ``alias_model_id`` value will set to the
        model ID of the ``model_name`` value, if provided, 
        """
        alias_name = re.sub(r'[^\w+]', '-', remove_accents(vals['alias_name'])).lower()
        alias_name = self._find_unique(cr, uid, alias_name, context=context)
        vals['alias_name'] = alias_name
        if model_name:
            model_id = self.pool.get('ir.model').search(cr, uid, [('model', '=', model_name)], context=context)[0]
            vals['alias_model_id'] = model_id
        return self.create(cr, uid, vals, context=context)
