# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
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

"""
The checkpoint is a model containing records to be reviewed by the end
users.  The connectors register records to verify so the user can check
them and flag them as reviewed.

A concrete use case is the import of new products from Magento. Once
they are imported, the user have to configure things like the supplier,
so they appears in this list.
"""

from openerp import models, fields, api, _


class ConnectorCheckpoint(models.Model):
    _name = 'connector.checkpoint'
    _description = 'Connector Checkpoint'

    _inherit = ['mail.thread', 'ir.needaction_mixin']

    @api.model
    def _reference_models(self):
        models = self.env['ir.model'].search([('state', '!=', 'manual')])
        return [(model.model, model.name)
                for model in models
                if not model.model.startswith('ir.')]

    @api.depends('model_id', 'record_id')
    def _compute_record(self):
        for check in self:
            check.record = check.model_id.model + ',' + str(check.record_id)

    @api.depends('model_id', 'record_id')
    def _compute_name(self):
        for check in self:
            model = self.env[check.model_id.model]
            check.name = model.browse(check.record_id).display_name

    @api.model
    def _search_record(self, operator, value):
        model_model = self.env['ir.model']
        sql = "SELECT DISTINCT model_id FROM connector_checkpoint"
        self.env.cr.execute(sql)
        model_ids = [row[0] for row in self.env.cr.fetchall()]
        models = model_model.browse(model_ids)

        ids = set()
        for model in models:
            model_id = model.id
            model_name = model.model
            model_obj = self.env[model_name]
            results = model_obj.name_search(name=value,
                                            operator=operator)
            res_ids = [res[0] for res in results]
            checks = self.search([('model_id', '=', model_id),
                                  ('record_id', 'in', res_ids)])
            ids.update(checks.ids)
        if not ids:
            return [('id', '=', '0')]
        return [('id', 'in', tuple(ids))]

    record = fields.Reference(
        compute='_compute_record',
        selection='_reference_models',
        help="The record to review.",
        readonly=True,
    )
    name = fields.Char(
        compute='_compute_name',
        search='_search_record',
        string='Record Name',
        help="Name of the record to review",
        readonly=True,
    )
    record_id = fields.Integer(string='Record ID',
                               required=True,
                               readonly=True)
    model_id = fields.Many2one(comodel_name='ir.model',
                               string='Model',
                               required=True,
                               readonly=True)
    backend_id = fields.Reference(
        string='Imported from',
        selection='_reference_models',
        readonly=True,
        required=True,
        help="The record has been imported from this backend",
        select=True,
    )
    state = fields.Selection(
        selection=[('need_review', 'Need Review'),
                   ('reviewed', 'Reviewed')],
        string='Status',
        required=True,
        readonly=True,
        default='need_review',
    )

    @api.multi
    def reviewed(self):
        return self.write({'state': 'reviewed'})

    @api.multi
    def _subscribe_users(self):
        """ Subscribe all users having the 'Connector Manager' group """
        group = self.env.ref('connector.group_connector_manager')
        if not group:
            return
        users = self.env['res.users'].search([('groups_id', '=', group.id)])
        self.message_subscribe_users(user_ids=users.ids)

    @api.model
    def create(self, vals):
        record = super(ConnectorCheckpoint, self).create(vals)
        record._subscribe_users()
        msg = _('A %s needs a review.') % record.model_id.name
        record.message_post(body=msg, subtype='mail.mt_comment',)
        return record

    @api.model
    def create_from_name(self, model_name, record_id,
                         backend_model_name, backend_id):
        model_model = self.env['ir.model']
        model = model_model.search([('model', '=', model_name)], limit=1)
        assert model, "The model %s does not exist" % model_name
        backend = backend_model_name + ',' + str(backend_id)
        return self.create({'model_id': model.id,
                            'record_id': record_id,
                            'backend_id': backend})

    @api.model
    def _needaction_domain_get(self):
        """ Returns the domain to filter records that require an action
            :return: domain or False is no action
        """
        return [('state', '=', 'need_review')]


def add_checkpoint(session, model_name, record_id,
                   backend_model_name, backend_id):
    checkpoint_model = session.env['connector.checkpoint']
    return checkpoint_model.create_from_name(model_name, record_id,
                                             backend_model_name, backend_id)


class connector_checkpoint_review(models.TransientModel):
    _name = 'connector.checkpoint.review'
    _description = 'Checkpoints Review'

    @api.model
    def _get_checkpoint_ids(self):
        res = False
        context = self.env.context
        if (context.get('active_model') == 'connector.checkpoint' and
                context.get('active_ids')):
            res = context['active_ids']
        return res

    checkpoint_ids = fields.Many2many(
        comodel_name='connector.checkpoint',
        relation='connector_checkpoint_review_rel',
        column1='review_id',
        column2='checkpoint_id',
        string='Checkpoints',
        domain="[('state', '=', 'need_review')]",
        default=_get_checkpoint_ids)

    @api.multi
    def review(self):
        self.checkpoint_ids.reviewed()
        return {'type': 'ir.actions.act_window_close'}
