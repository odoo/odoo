from odoo import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)


class L10n_Latam_Checkbook(models.Model):

    _name = 'l10n_latam.checkbook'
    _description = 'Checkbook'

    name = fields.Char(compute='_compute_name',)
    sequence_id = fields.Many2one(
        'ir.sequence', 'Sequence', copy=False, domain=[('code', '=', 'own_check')],
        help="Checks numbering sequence.", context={'default_code': 'l10n_latam.checkbook'},)
    next_number = fields.Integer(related='sequence_id.number_next_actual', related_sudo=True, readonly=False)
    type = fields.Selection(
        [('deferred', 'Deferred'), ('currents', 'Currents'), ('electronic', 'Electronic')],
        string='Check type', required=True, default='deferred')
    journal_id = fields.Many2one(
        'account.journal', 'Journal', readonly=True, required=True, ondelete='cascade',)
    range_to = fields.Integer(
        'To Number',
        help='If you set a number here, this checkbook will be automatically'
        ' set as used when this number is raised.'
    )
    active = fields.Boolean(default=True)

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if not rec.sequence_id:
            rec._create_sequence(vals.get('next_number', 0))
        return rec

    def _create_sequence(self, next_number):
        """ Create a check sequence for the checkbook """
        for rec in self:
            rec.sequence_id = rec.env['ir.sequence'].sudo().create({
                'name': '%s - %s' % (rec.journal_id.name, rec.name),
                'implementation': 'no_gap',
                'padding': 8,
                'number_increment': 1,
                'code': 'acccount.checkbook',
                'number_next_actual': next_number,
                'company_id': rec.journal_id.company_id.id,
            })

    @api.depends('type', 'range_to')
    def _compute_name(self):
        for rec in self:
            if not rec.type:
                rec.name = False
                continue
            name = {
                'deferred': _('Deferred Checks'),
                'currents': _('Currents Checks'),
                'electronic': _('Electronic Checks')}.get(rec.type)
            if rec.range_to:
                name += _(' up to %s') % rec.range_to
            rec.name = name
