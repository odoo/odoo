from odoo import models, api, fields


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    secure_sequence_id = fields.Many2one('ir.sequence',
        help='Sequence to use to ensure the securisation of data',
        readonly=True, copy=False)


class Picking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'blockchain.mixin', 'l10n_pt.mixin']

    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id.country_id'])
    l10n_pt_date = fields.Date(string="Date of the document used for the signature", compute='_compute_l10n_pt_date')
    l10n_pt_gross_total = fields.Float(string="Gross total of the document used for the signature", default=0.0)

    def _compute_l10n_pt_date(self):
        for picking in self:
            picking.l10n_pt_date = picking.date_done.date()

    def _action_done(self):
        if self._context.get('l10n_pt_stock_compute_hash', True):
            self._compute_l10n_pt_document_number()
        return super()._action_done()

    # Override l10n_pt.mixin
    def _compute_l10n_pt_document_number(self):
        for picking in self.filtered(lambda p: (
            p.country_code == 'PT'
            and p.picking_type_id.code == 'outgoing'
            and p.picking_type_id.sequence_code
            and p.name
            and not p.l10n_pt_document_number
        )):
            if hasattr(picking, 'pos_order_id') and picking.pos_order_id:
                continue  # POS orders are hashed in their own way (see l10n_pt_pos)
            picking_type = picking.picking_type_id
            seq_info = self._l10n_pt_get_sanitized_sequence_info(picking_type.sequence_code, name=picking.name)
            picking.l10n_pt_document_number = f'{picking_type.code} {seq_info}'

    def _get_blockchain_inalterable_hash_fields(self):
        if self.company_id.country_id.code != 'PT':
            return super()._get_blockchain_inalterable_hash_fields()
        return ['date_done', 'create_date', 'l10n_pt_document_number', 'name']

    def _get_blockchain_sorting_keys(self):
        if self.company_id.country_id.code != 'PT':
            return super()._get_blockchain_sorting_keys()
        return ['date_done', 'id']

    def _get_blockchain_secure_sequence(self):
        self.ensure_one()
        if self.company_id.country_id.code != 'PT':
            return super()._get_blockchain_secure_sequence()
        self.env['blockchain.mixin']._create_blockchain_secure_sequence(self.picking_type_id, 'secure_sequence_id', self.company_id.id)
        return self.picking_type_id.secure_sequence_id

    def _get_blockchain_previous_record_domain(self):
        if self.company_id.country_id.code != 'PT':
            return super()._get_blockchain_previous_record_domain()
        res = [
            ('state', '=', 'done'),
            ('picking_type_id.code', '=', 'outgoing'),
            ('company_id', '=', self.company_id.id),
            ('id', '!=', self.id),
            ('blockchain_secure_sequence_number', '<', self.blockchain_secure_sequence_number),
            ('blockchain_secure_sequence_number', '!=', 0)
        ]
        if hasattr(self, 'pos_order_id'):
            res.append(('pos_order_id', '=', False))
        return res

    @api.depends('country_code', 'picking_type_id.code', 'state', 'date_done', 'l10n_pt_document_number')
    def _compute_blockchain_must_hash(self):
        super()._compute_blockchain_must_hash()
        for picking in self:
            picking.blockchain_must_hash = (
                picking.blockchain_must_hash
                or picking.blockchain_secure_sequence_number
                or picking.l10n_pt_document_number
            )

    def _get_blockchain_record_hash_string(self, previous_hash=None):
        self.ensure_one()
        if self.company_id.country_id.code != 'PT':
            return super()._get_blockchain_record_hash_string(previous_hash)
        return self._l10n_pt_get_blockchain_record_hash_string(previous_hash)

    def _compute_blockchain_inalterable_hash(self):
        """
        We need an optimization for Portugal where the hash is only computed
        when we actually need it (printing of a stock picking, delivery slip or the integrity report).
        This is because in Portugal's case, the hash is computed by Odoo's IAP
        service which needs an RPC call that might be slow.
        """
        super(Picking, self.filtered(lambda p: p.company_id.country_id.code != 'PT'))._compute_blockchain_inalterable_hash()
        if self._context.get('l10n_pt_force_compute_signature'):
            super(Picking, self.filtered(lambda p: p.company_id.country_id.code == 'PT'))._l10n_pt_compute_blockchain_inalterable_hash()

    @api.model
    def _l10n_pt_stock_cron_compute_missing_hashes(self):
        companies = self.env['res.company'].search([]).filtered(lambda c: c.country_id.code == 'PT')
        for company in companies:
            self.env['stock.picking'].l10n_pt_compute_missing_hashes(company.id)
