from odoo import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)


class L10nLatamCheckbook(models.Model):

    _name = 'l10n_latam.checkbook'
    _description = 'Checkbook'
    _rec_name = 'sequence_id'
    _order = 'active desc, range_to'

    sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string='Sequence',
        domain=[('code', '=', 'own_check')],
        copy=False,
        help="Checks numbering sequence.",
    )
    next_number = fields.Integer(
        related='sequence_id.number_next_actual', related_sudo=True,
        readonly=False,
    )
    type = fields.Selection(
        selection=[('deferred', 'Deferred'), ('currents', 'Currents'), ('electronic', 'Electronic')],
        string='Check type',
        default='deferred',
        required=True,
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        readonly=True,
        required=True,
        ondelete='cascade',
    )
    range_to = fields.Integer(
        string='To Number',
    )
    active = fields.Boolean(
        default=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec, vals in zip(recs, vals_list):
            if not rec.sequence_id:
                rec._create_sequence(vals.get('next_number', 0))
        return recs

    def _create_sequence(self, next_number):
        """ Create a check sequence for the checkbook """
        for rec in self:
            rec.sequence_id = rec.env['ir.sequence'].sudo().create({
                'name': '%s - %s' % (rec.journal_id.name, rec.display_name),
                'implementation': 'no_gap',
                'padding': 8,
                'number_increment': 1,
                'code': 'l10n_latam.checkbook',
                'number_next_actual': next_number,
                'company_id': rec.journal_id.company_id.id,
            })

    def name_get(self):
        result = []
        for rec in self:
            name = {
                'deferred': _('Deferred Checks'),
                'currents': _('Currents Checks'),
                'electronic': _('Electronic Checks')
            }.get(rec.type, '')
            if rec.range_to:
                name += _(' up to %s', rec.range_to)
            result.append((rec.id, name))
        return result
