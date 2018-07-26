# -*- coding: utf-8 -*-

import logging
import re
import unicodedata

from openerp import _, api, fields, models, SUPERUSER_ID
from openerp.exceptions import UserError
from openerp.modules.registry import RegistryManager
from openerp.tools import ustr
from openerp.tools.safe_eval import safe_eval as eval

_logger = logging.getLogger(__name__)


# Inspired by http://stackoverflow.com/questions/517923
def remove_accents(input_str):
    """Suboptimal-but-better-than-nothing way to replace accented
    latin letters by an ASCII equivalent. Will obviously change the
    meaning of input_str and work only for some cases"""
    input_str = ustr(input_str)
    nkfd_form = unicodedata.normalize('NFKD', input_str)
    return u''.join([c for c in nkfd_form if not unicodedata.combining(c)])


class Alias(models.Model):
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

    alias_name = fields.Char('Alias Name', help="The name of the email alias, e.g. 'jobs' if you want to catch emails for <jobs@example.odoo.com>")
    alias_model_id = fields.Many2one('ir.model', 'Aliased Model', required=True, ondelete="cascade",
                                     help="The model (Odoo Document Kind) to which this alias "
                                          "corresponds. Any incoming email that does not reply to an "
                                          "existing record will cause the creation of a new record "
                                          "of this model (e.g. a Project Task)",
                                      # hack to only allow selecting mail_thread models (we might
                                      # (have a few false positives, though)
                                      domain="[('field_id.name', '=', 'message_ids')]")
    alias_user_id = fields.Many2one('res.users', 'Owner', defaults=lambda self: self.env.user,
                                    help="The owner of records created upon receiving emails on this alias. "
                                         "If this field is not set the system will attempt to find the right owner "
                                         "based on the sender (From) address, or will use the Administrator account "
                                         "if no system user is found for that address.")
    alias_defaults = fields.Text('Default Values', required=True, default='{}',
                                 help="A Python dictionary that will be evaluated to provide "
                                      "default values when creating new records for this alias.")
    alias_force_thread_id = fields.Integer(
        'Record Thread ID',
        help="Optional ID of a thread (record) to which all incoming messages will be attached, even "
             "if they did not reply to it. If set, this will disable the creation of new records completely.")
    alias_domain = fields.Char('Alias domain', compute='_get_alias_domain',
                               default=lambda self: self.env["ir.config_parameter"].get_param("mail.catchall.domain"))
    alias_parent_model_id = fields.Many2one(
        'ir.model', 'Parent Model',
        help="Parent model holding the alias. The model holding the alias reference "
             "is not necessarily the model given by alias_model_id "
             "(example: project (parent_model) and task (model))")
    alias_parent_thread_id = fields.Integer('Parent Record Thread ID', help="ID of the parent record holding the alias (example: project holding the task creation alias)")
    alias_contact = fields.Selection([
        ('everyone', 'Everyone'),
        ('partners', 'Authenticated Partners'),
        ('followers', 'Followers only')], default='everyone',
        string='Alias Contact Security', required=True,
        help="Policy to post a message on the document using the mailgateway.\n"
             "- everyone: everyone can post\n"
             "- partners: only authenticated partners\n"
             "- followers: only followers of the related document or members of following channels\n")

    _sql_constraints = [
        ('alias_unique', 'UNIQUE(alias_name)', 'Unfortunately this email alias is already used, please choose a unique one')
    ]

    @api.multi
    def _get_alias_domain(self):
        alias_domain = self.env["ir.config_parameter"].get_param("mail.catchall.domain")
        for record in self:
            record.alias_domain = alias_domain

    @api.one
    @api.constrains('alias_defaults')
    def _check_alias_defaults(self):
        try:
            dict(eval(self.alias_defaults))
        except Exception:
            raise UserError(_('Invalid expression, it must be a literal python dictionary definition e.g. "{\'field\': \'value\'}"'))

    @api.model
    def create(self, vals):
        """ Creates an email.alias record according to the values provided in ``vals``,
            with 2 alterations: the ``alias_name`` value may be suffixed in order to
            make it unique (and certain unsafe characters replaced), and
            he ``alias_model_id`` value will set to the model ID of the ``model_name``
            context value, if provided.
        """
        model_name = self._context.get('alias_model_name')
        parent_model_name = self._context.get('alias_parent_model_name')
        if vals.get('alias_name'):
            vals['alias_name'] = self._clean_and_make_unique(vals.get('alias_name'))
        if model_name:
            model = self.env['ir.model'].search([('model', '=', model_name)])
            vals['alias_model_id'] = model.id
        if parent_model_name:
            model = self.env['ir.model'].search([('model', '=', parent_model_name)])
            vals['alias_parent_model_id'] = model.id
        return super(Alias, self).create(vals)

    @api.multi
    def write(self, vals):
        """"give a unique alias name if given alias name is already assigned"""
        if vals.get('alias_name') and self.ids:
            vals['alias_name'] = self._clean_and_make_unique(vals.get('alias_name'), alias_ids=self.ids)
        return super(Alias, self).write(vals)

    @api.multi
    def name_get(self):
        """Return the mail alias display alias_name, including the implicit
           mail catchall domain if exists from config otherwise "New Alias".
           e.g. `jobs@mail.odoo.com` or `jobs` or 'New Alias'
        """
        res = []
        for record in self:
            if record.alias_name and record.alias_domain:
                res.append((record['id'], "%s@%s" % (record.alias_name, record.alias_domain)))
            elif record.alias_name:
                res.append((record['id'], "%s" % (record.alias_name)))
            else:
                res.append((record['id'], _("Inactive Alias")))
        return res

    @api.model
    def _find_unique(self, name, alias_ids=False):
        """Find a unique alias name similar to ``name``. If ``name`` is
           already taken, make a variant by adding an integer suffix until
           an unused alias is found.
        """
        sequence = None
        while True:
            new_name = "%s%s" % (name, sequence) if sequence is not None else name
            domain = [('alias_name', '=', new_name)]
            if alias_ids:
                domain += [('id', 'not in', alias_ids)]
            if not self.search(domain):
                break
            sequence = (sequence + 1) if sequence else 2
        return new_name

    @api.model
    def _clean_and_make_unique(self, name, alias_ids=False):
        # when an alias name appears to already be an email, we keep the local part only
        name = remove_accents(name).lower().split('@')[0]
        name = re.sub(r'[^\w+.]+', '-', name)
        return self._find_unique(name, alias_ids=alias_ids)

    def migrate_to_alias(self, cr, child_model_name, child_table_name, child_model_auto_init_fct,
        alias_model_name, alias_id_column, alias_key, alias_prefix='', alias_force_key='', alias_defaults={},
        alias_generate_name=False, context=None):
        """ Installation hook to create aliases for all users and avoid constraint errors.

            :param child_model_name: model name of the child class (i.e. res.users)
            :param child_table_name: table name of the child class (i.e. res_users)
            :param child_model_auto_init_fct: pointer to the _auto_init function
                (i.e. super(res_users,self)._auto_init(cr, context=context))
            :param alias_model_name: name of the aliased model
            :param alias_id_column: alias_id column (i.e. self._columns['alias_id'])
            :param alias_key: name of the column used for the unique name (i.e. 'login')
            :param alias_prefix: prefix for the unique name (i.e. 'jobs' + ...)
            :param alias_force_key': name of the column for force_thread_id;
                if empty string, not taken into account
            :param alias_defaults: dict, keys = mail.alias columns, values = child
                model column name used for default values (i.e. {'job_id': 'id'})
            :param alias_generate_name: automatically generate alias name using prefix / alias key;
                default alias_name value is False because since 8.0 it is not required anymore
        """
        if context is None:
            context = {}

        # disable the unique alias_id not null constraint, to avoid spurious warning during
        # super.auto_init. We'll reinstall it afterwards.
        alias_id_column.required = False

        # call _auto_init
        res = child_model_auto_init_fct(cr, context=context)

        registry = RegistryManager.get(cr.dbname)
        mail_alias = registry.get('mail.alias')
        child_class_model = registry[child_model_name]
        no_alias_ids = child_class_model.search(cr, SUPERUSER_ID, [('alias_id', '=', False)], context={'active_test': False})
        # Use read() not browse(), to avoid prefetching uninitialized inherited fields
        for obj_data in child_class_model.read(cr, SUPERUSER_ID, no_alias_ids, [alias_key]):
            alias_vals = {'alias_name': False}
            if alias_generate_name:
                alias_vals['alias_name'] = '%s%s' % (alias_prefix, obj_data[alias_key])
            if alias_force_key:
                alias_vals['alias_force_thread_id'] = obj_data[alias_force_key]
            alias_vals['alias_defaults'] = dict((k, obj_data[v]) for k, v in alias_defaults.iteritems())
            alias_vals['alias_parent_thread_id'] = obj_data['id']
            alias_create_ctx = dict(context, alias_model_name=alias_model_name, alias_parent_model_name=child_model_name)
            alias_id = mail_alias.create(cr, SUPERUSER_ID, alias_vals, context=alias_create_ctx)
            child_class_model.write(cr, SUPERUSER_ID, obj_data['id'], {'alias_id': alias_id}, context={'mail_notrack': True})
            _logger.info('Mail alias created for %s %s (id %s)', child_model_name, obj_data[alias_key], obj_data['id'])

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
        return res

    @api.multi
    def open_document(self):
        if not self.alias_model_id or not self.alias_force_thread_id:
            return False
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self.alias_model_id.model,
            'res_id': self.alias_force_thread_id,
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def open_parent_document(self):
        if not self.alias_parent_model_id or not self.alias_parent_thread_id:
            return False
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self.alias_parent_model_id.model,
            'res_id': self.alias_parent_thread_id,
            'type': 'ir.actions.act_window',
        }
