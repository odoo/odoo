from odoo import models, fields, api

class OnedeskIntegrationLog(models.Model):
    _name = 'onedesk.integration.log'
    _description = 'Log de synchronisation'
    _order = 'create_date desc'

    integration_id = fields.Many2one('onedesk.integration', required=True, ondelete='cascade')
    log_type = fields.Selection([
        ('success', '✅ Succès'),
        ('error', '❌ Erreur'),
        ('warning', '⚠️ Avertissement'),
        ('info', 'ℹ️ Information'),
    ], required=True)
    message = fields.Text(required=True)
    create_date = fields.Datetime(string='Date', readonly=True)