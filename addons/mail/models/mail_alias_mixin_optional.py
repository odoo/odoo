# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AliasMixinOptional(models.AbstractModel):
    """ A mixin for models that handles underlying 'mail.alias' records to use
    the mail gateway. Field is not mandatory and its creation is done dynamically
    based on given 'alias_name', allowing to gradually populate the alias table
    without having void aliases as when used with an inherits-like implementation.
    """
    _name = 'mail.alias.mixin.optional'
    _description = 'Email Aliases Mixin (light)'
    ALIAS_WRITEABLE_FIELDS = ['alias_name', 'alias_contact', 'alias_defaults', 'alias_bounced_content']

    alias_id = fields.Many2one('mail.alias', string='Alias', ondelete="restrict", required=False)
    alias_name = fields.Char(related='alias_id.alias_name', readonly=False)
    alias_domain = fields.Char('Alias domain', compute='_compute_alias_domain')
    alias_defaults = fields.Text(related='alias_id.alias_defaults')
    alias_email = fields.Char('Email Alias', compute='_compute_alias_email')

    @api.depends('alias_name')
    def _compute_alias_domain(self):
        self.alias_domain = self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")

    @api.depends('alias_domain', 'alias_name')
    def _compute_alias_email(self):
        """ Alias email can be used in views, as it is Falsy when having no domain
        or no name. Alias display name itself contains more info and cannot be
        used as it is in views. """
        self.alias_email = False
        for record in self.filtered(lambda rec: rec.alias_name and rec.alias_domain):
            record.alias_email = f"{record.alias_name}@{record.alias_domain}"

    # --------------------------------------------------
    # CRUD
    # --------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """ Create aliases using sudo if an alias is required, notably if its
        name is given. """
        # prepare all alias values
        alias_vals_list, record_vals_list = [], []
        for vals in vals_list:
            if vals.get('alias_name'):
                vals['alias_name'] = self.env['mail.alias']._sanitize_alias_name(vals['alias_name'])
            if self._require_new_alias(vals):
                alias_vals, record_vals = self._alias_filter_fields(vals)
                # generate record-agnostic base alias values
                alias_vals.update(self.env[self._name]._alias_get_creation_values())
                alias_vals_list.append(alias_vals)
                record_vals_list.append(record_vals)

        # create all aliases
        alias_ids = []
        if alias_vals_list:
            alias_ids = iter(self.env['mail.alias'].sudo().create(alias_vals_list).ids)

        # update alias values in create vals directly
        valid_vals_list = []
        record_vals_iter = iter(record_vals_list)
        for vals in vals_list:
            if self._require_new_alias(vals):
                record_vals = next(record_vals_iter)
                record_vals['alias_id'] = next(alias_ids)
                valid_vals_list.append(record_vals)
            else:
                valid_vals_list.append(vals)

        records = super().create(valid_vals_list)

        for record in records.filtered('alias_id'):
            record.alias_id.sudo().write(record._alias_get_creation_values())

        return records

    def write(self, vals):
        """ Split writable fields of mail.alias and other fields alias fields will
        write with sudo and the other normally. If alias does not exist and we
        try to set a name, create the alias automatically. """
        # create missing aliases
        if vals.get('alias_name'):
            alias_create_values = [
                dict(
                    record._alias_get_creation_values(),
                    alias_name=self.env['mail.alias']._sanitize_alias_name(vals['alias_name']),
                )
                for record in self.filtered(lambda rec: not rec.alias_id)
            ]
            if alias_create_values:
                aliases = self.env['mail.alias'].sudo().create(alias_create_values)
                for record, alias in zip(self.filtered(lambda rec: not rec.alias_id), aliases):
                    record.alias_id = alias.id

        alias_vals, record_vals = self._alias_filter_fields(vals, filters=self.ALIAS_WRITEABLE_FIELDS)
        if record_vals:
            super().write(record_vals)
        if alias_vals and (record_vals or self.check_access_rights('write', raise_exception=False)):
            self.mapped('alias_id').sudo().write(alias_vals)

        return True

    def unlink(self):
        """ Delete the given records, and cascade-delete their corresponding alias. """
        aliases = self.mapped('alias_id')
        res = super().unlink()
        aliases.sudo().unlink()
        return res

    @api.returns(None, lambda value: value[0])
    def copy_data(self, default=None):
        data = super().copy_data(default)[0]
        for fields_not_writable in set(self.env['mail.alias']._fields.keys()) - set(self.ALIAS_WRITEABLE_FIELDS):
            if fields_not_writable in data:
                del data[fields_not_writable]
        return [data]

    @api.model
    def _require_new_alias(self, record_vals):
        """ Create only if no existing alias, and if a name is given, to avoid
        creating inactive aliases (falsy name). """
        return not record_vals.get('alias_id') and record_vals.get('alias_name')

    # --------------------------------------------------
    # MIXIN TOOL OVERRIDE METHODS
    # --------------------------------------------------

    def _alias_get_creation_values(self):
        """ Return values to create an alias, or to write on the alias after its
            creation.
        """
        return {
            'alias_parent_thread_id': self.id if self.id else False,
            'alias_parent_model_id': self.env['ir.model']._get_id(self._name),
        }

    def _alias_filter_fields(self, values, filters=False):
        """ Split the vals dict into two dictionnary of vals, one for alias
        field and the other for other fields """
        if not filters:
            filters = self.env['mail.alias']._fields.keys()
        alias_values, record_values = {}, {}
        for fname in values.keys():
            if fname in filters:
                alias_values[fname] = values.get(fname)
            else:
                record_values[fname] = values.get(fname)
        return alias_values, record_values
