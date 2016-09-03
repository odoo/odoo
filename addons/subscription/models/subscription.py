# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# TODO:
#   Error treatment: exception, request, ... -> send request to user_id

from odoo import api, fields, models, _
from odoo.exceptions import UserError


def _get_document_types(self):
    return [(doc.model.model, doc.name) for doc in self.env['subscription.document'].search([], order='name')]


class SubscriptionDocument(models.Model):
    _name = "subscription.document"
    _description = "Subscription Document"

    name = fields.Char(required=True)
    active = fields.Boolean(help="If the active field is set to False, it will allow you to hide the subscription document without removing it.", default=True)
    model = fields.Many2one('ir.model', string="Object", required=True)
    field_ids = fields.One2many('subscription.document.fields', 'document_id', string='Fields', copy=True)


class SubscriptionDocumentFields(models.Model):
    _name = "subscription.document.fields"
    _description = "Subscription Document Fields"
    _rec_name = 'field'

    field = fields.Many2one('ir.model.fields', domain="[('model_id', '=', parent.model)]", required=True)
    value = fields.Selection([('false', 'False'), ('date', 'Current Date')], string='Default Value', help="Default value is considered for field when new document is generated.")
    document_id = fields.Many2one('subscription.document', string='Subscription Document', ondelete='cascade')


class Subscription(models.Model):
    _name = "subscription.subscription"
    _description = "Subscription"

    name = fields.Char(required=True)
    active = fields.Boolean(help="If the active field is set to False, it will allow you to hide the subscription without removing it.", default=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    notes = fields.Text(string='Internal Notes')
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user)
    interval_number = fields.Integer(string='Internal Qty', default=1)
    interval_type = fields.Selection([('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')], string='Interval Unit', default='months')
    exec_init = fields.Integer(string='Number of Documents')
    date_init = fields.Datetime(string='First Date', default=fields.Datetime.now)
    state = fields.Selection([('draft', 'Draft'), ('running', 'Running'), ('done', 'Done')], string='Status', copy=False, default='draft')
    doc_source = fields.Reference(selection=_get_document_types, string='Source Document', required=True, help="User can choose the source document on which he wants to create documents")
    doc_lines = fields.One2many('subscription.subscription.history', 'subscription_id', string='Documents created', readonly=True)
    cron_id = fields.Many2one('ir.cron', string='Cron Job', help="Scheduler which runs on subscription", states={'running': [('readonly', True)], 'done': [('readonly', True)]})
    note = fields.Text(string='Notes', help="Description or Summary of Subscription")

    @api.model
    def _auto_end(self):
        super(Subscription, self)._auto_end()
        # drop the FK from subscription to ir.cron, as it would cause deadlocks
        # during cron job execution. When model_copy() tries to write() on the subscription,
        # it has to wait for an ExclusiveLock on the cron job record, but the latter
        # is locked by the cron system for the duration of the job!
        # FIXME: the subscription module should be reviewed to simplify the scheduling process
        #        and to use a unique cron job for all subscriptions, so that it never needs to
        #        be updated during its execution.
        self.env.cr.execute("ALTER TABLE %s DROP CONSTRAINT %s" % (self._table, '%s_cron_id_fkey' % self._table))

    @api.multi
    def set_process(self):
        for subscription in self:
            cron_data = {
                'name': subscription.name,
                'interval_number': subscription.interval_number,
                'interval_type': subscription.interval_type,
                'numbercall': subscription.exec_init,
                'nextcall': subscription.date_init,
                'model': self._name,
                'args': repr([[subscription.id]]),
                'function': '_cron_model_copy',
                'priority': 6,
                'user_id': subscription.user_id.id
            }
            cron = self.env['ir.cron'].sudo().create(cron_data)
            subscription.write({'cron_id': cron.id, 'state': 'running'})

    @api.model
    def _cron_model_copy(self, ids):
        self.browse(ids).model_copy()

    @api.multi
    def model_copy(self):
        for subscription in self.filtered(lambda sub: sub.cron_id):
            if not subscription.doc_source.exists():
                raise UserError(_('Please provide another source document.\nThis one does not exist!'))

            default = {'state': 'draft'}
            documents = self.env['subscription.document'].search([('model.model', '=', subscription.doc_source._name)], limit=1)
            fieldnames = dict((f.field.name, f.value == 'date' and fields.Date.today() or False)
                               for f in documents.field_ids)
            default.update(fieldnames)

            # if there was only one remaining document to generate
            # the subscription is over and we mark it as being done
            if subscription.cron_id.numbercall == 1:
                subscription.write({'state': 'done'})
            else:
                subscription.write({'state': 'running'})
            copied_doc = subscription.doc_source.copy(default)
            self.env['subscription.subscription.history'].create({
                'subscription_id': subscription.id,
                'date': fields.Datetime.now(),
                'document_id': '%s,%s' % (subscription.doc_source._name, copied_doc.id)})

    @api.multi
    def unlink(self):
        if any(self.filtered(lambda s: s.state == "running")):
            raise UserError(_('You cannot delete an active subscription!'))
        return super(Subscription, self).unlink()

    @api.multi
    def set_done(self):
        self.mapped('cron_id').write({'active': False})
        self.write({'state': 'done'})

    @api.multi
    def set_draft(self):
        self.write({'state': 'draft'})


class SubscriptionHistory(models.Model):
    _name = "subscription.subscription.history"
    _description = "Subscription history"
    _rec_name = 'date'

    date = fields.Datetime()
    subscription_id = fields.Many2one('subscription.subscription', string='Subscription', ondelete='cascade')
    document_id = fields.Reference(selection=_get_document_types, string='Source Document', required=True)
