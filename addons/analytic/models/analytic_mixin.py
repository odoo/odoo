# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AnalyticParentMixin(models.AbstractModel):
    _name = 'analytic.parent.mixin'
    _description = 'Analytic Parent Mixin'

    track_cost = fields.Boolean("Track Cost", default=False)
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", copy=False, ondelete='set null',
        help="Analytic account to which this project is linked for financial management."
             "Use an analytic account to record cost and revenue on your project.")

    # ---------------------------------------------------------
    # CRUD and ORM Methods
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, list_values):
        """ Create an analytic account if record allow timesheet and don't provide one
            Note: create it before calling super() to avoid raising the ValidationError from _check_allow_timesheet
        """
        default_track_cost = self.default_get(['track_cost'])['track_cost']
        for values in list_values:
            track_cost = values['track_cost'] if 'track_cost' in values else default_track_cost
            if track_cost and not values.get('analytic_account_id'):
                analytic_account_values = self._analytic_create_account_extract_values(values)
                analytic_account = self.env['account.analytic.account'].create(analytic_account_values)
                values['analytic_account_id'] = analytic_account.id
        return super(AnalyticParentMixin, self).create(list_values)

    @api.multi
    def write(self, values):
        # create the AA for record still allowing timesheet
        if values.get('track_cost'):
            for record in self:
                if not record.analytic_account_id and not values.get('analytic_account_id'):
                    record._analytic_create_account()
        result = super(AnalyticParentMixin, self).write(values)
        return result

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    @api.model
    def _analytic_create_account_extract_values(self, values):
        """ Extract value to create an analytic account from the `create` value of the record
            implementing the analytic.parent.mixin
        """
        default_company_id = self._default_get(['company_id'])['company_id']
        return {
            'name': values.get(self._rec_name, _('Unknown Analytic Account')),
            'active': True,
            'partner_id': values.get('partner_id') if hasattr(self, 'partner_id') else False,
            'company_id': values.get('company_id', default_company_id) if hasattr(self, 'company_id') else default_company_id,
        }

    @api.model
    def _init_data_analytic_account(self):
        self.search([('analytic_account_id', '=', False), ('track_cost', '=', True)])._analytic_create_account()

    def _analytic_create_account(self):
        for record in self:
            values = record._analytic_create_prepare_values()
            analytic_account = self.env['account.analytic.account'].create(values)
            record.write({'analytic_account_id': analytic_account.id})

    def _analytic_create_account_prepare_values(self):
        """ Retrun the value required to create an analytic account from an existing record
            inheriting the parent.service.mixin
        """
        values = {
            'name': self.display_name,
            'active': True,
        }
        if hasattr(self, 'partner_id'):
            values['partner_id'] = self.parent_id.id
        if hasattr(self, 'company_id'):
            values['company_id'] = self.company_id.id
        return values


class AnalyticPackMixin(models.AbstractModel):
    _name = 'analytic.pack.mixin'
    _description = 'Analytic Pack Mixin'
    _analytic_parent_field = None

    analytic_pack_id = fields.Many2one('analytic.pack', string="Analytic Pack")
    analytic_account_id = fields.Many2one('account.analytic.account', related='analytic_pack_id.analytic_account_id', readonly=False)

    # ---------------------------------------------------------
    # CRUD Methods
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, list_values):
        # get a map for project_id --> analytic_account_id
        parent_analytic_account_map = self._analytic_find_default_parent_account(list_values)

        pack_value_list = []
        pack_parent_index = {}
        for index, vals in enumerate(list_values):
            if not vals.get('analytic_pack_id'):  # if the pack is not given, check to create one
                pack_vals = self._analytic_create_pack_extract_values(vals, parent_analytic_account_map)
                if pack_vals:  # if the parent has an AA set, then create the pack
                    pack_value_list.append(pack_vals)
                    pack_parent_index[index] = len(pack_value_list) - 1

        services = self.env['analytic.pack'].create(pack_value_list)

        for index, vals in enumerate(list_values):
            if pack_parent_index.get(index):
                vals['analytic_pack_id'] = services[pack_parent_index.get(index)].id

        return super(AnalyticPackMixin, self).create(list_values)

    # ---------------------------------------------------------
    # Business / Helpers Methods
    # ---------------------------------------------------------

    def _analytic_find_default_parent_account(self, list_values):
        """ From a create list of values, deduced the default analytic accound from the parent record. This requires
            the attribute `_analytic_parent_field` to be set.
        """
        parent_field_name = self._analytic_parent_field
        parent_res_model = self._fields[parent_field_name].comodel_name

        parent_ids = [vals[parent_field_name] for vals in list_values if vals.get(parent_field_name)]
        parent_analytic_account_map = {record.id: record.analytic_account_id.id for record in self.env[parent_res_model].browse(parent_ids)}

        return parent_analytic_account_map

    def _analytic_create_pack_extract_values(self, values, parent_default_analytic_account_map):
        """ Extract values to create a pack from the values to create the current model
            :param values: values to create a current record (implementing the mixin)
            :param parent_default_analytic_account_map: map of default analytic_account_id per record parent
            :returns values to create an analytic.pack, None if not analytic account can be deduced
        """
        analytic_account_id = values.pop('analytic_account_id', False)
        if not analytic_account_id and self._analytic_parent_field in values:
            analytic_account_id = parent_default_analytic_account_map.get(values[self._analytic_parent_field])
        if analytic_account_id:
            return {
                'name': values.get(self._rec_name, "Unknown Service"),
                'analytic_account_id': analytic_account_id,
                'res_model': self._name,
            }
        return None

    def _analytic_create_pack(self):
        list_values = []
        for record in self:
            list_values.append(record._analytic_create_pack_prepare_values())
        packs = self.env['analytic.pack'].create(list_values)
        for index, record in enumerate(self):
            record.write({'analytic_pack_id': packs[index].id})

    def _analytic_create_pack_prepare_values(self):
        return {
            'name': self.display_name,
            'res_model': self._name,
            'analytic_account_id': self[self._analytic_parent_field].analytic_account_id.id
        }
