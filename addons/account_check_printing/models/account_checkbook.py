##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)


class AccountCheckbook(models.Model):

    _name = 'account.checkbook'
    _description = 'Account Checkbook'

    name = fields.Char(
        compute='_compute_name',
    )
    sequence_id = fields.Many2one(
        'ir.sequence',
        'Sequence',
        copy=False,
        domain=[('code', '=', 'own_check')],
        help="Checks numbering sequence.",
        context={'default_code': 'account.checkbook'},
    )
    next_number = fields.Integer(
        'Next Number',
        # usamos compute y no related para poder usar sudo cuando se setea
        # secuencia sin necesidad de dar permiso en ir.sequence
        compute='_compute_next_number',
        inverse='_inverse_next_number',
    )
    type = fields.Selection(
        [('deferred', 'Deferred'), ('currents', 'Currents'), ('electronic', 'Electronic')],
        string='Check type',
        required=True,
        default='deferred',
        help='* Con cheques corrientes el asiento generado por el pago '
        'descontará directamente de la cuenta de banco y además la fecha de '
        'pago no es obligatoria.\n'
        '* Con cheques diferidos el asiento generado por el pago se hará '
        'contra la cuenta definida para tal fin en la compañía, luego será '
        'necesario el asiento de débito que se puede generar desde el extracto'
        ' o desde el cheque.',
    )
    journal_id = fields.Many2one(
        'account.journal', 'Journal',
        readonly=True,
        required=True,
        ondelete='cascade',
        states={'draft': [('readonly', False)]},
    )
    range_to = fields.Integer(
        'To Number',
        # readonly=True,
        # states={'draft': [('readonly', False)]},
        help='If you set a number here, this checkbook will be automatically'
        ' set as used when this number is raised.'
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('active', 'In Use'), ('used', 'Used')],
        string='State',
        # readonly=True,
        default='active',
        copy=False,
    )
    numerate_on_printing = fields.Boolean(
        default=False,
        string='Numerate on printing?',
        # readonly=True,
        # states={'draft': [('readonly', False)]},
        help='No number will be assigne while creating payment, number will be'
        'assigned after printing check.'
    )

    @api.depends('sequence_id.number_next_actual')
    def _compute_next_number(self):
        for rec in self:
            rec.next_number = rec.sequence_id.number_next_actual

    def _inverse_next_number(self):
        for rec in self.filtered('sequence_id'):
            rec.sequence_id.sudo().number_next_actual = rec.next_number

    @api.model
    def create(self, vals):
        rec = super(AccountCheckbook, self).create(vals)
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
                # si no lo pasamos, en la creacion se setea 1
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
