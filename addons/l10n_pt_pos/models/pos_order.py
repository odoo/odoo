from odoo import models, api, fields


class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = ['pos.order', 'blockchain.mixin', 'l10n_pt.mixin']

    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id.country_id'])
    l10n_pt_date = fields.Date(string="Date of the document used for the signature", compute='_compute_l10n_pt_date')
    l10n_pt_gross_total = fields.Float(string="Gross total of the document used for the signature", related='amount_total')

    def _compute_l10n_pt_date(self):
        for order in self:
            order.l10n_pt_date = order.date_order.date()

    def _create_order_picking(self):
        return super(PosOrder, self.with_context(l10n_pt_stock_compute_hash=False))._create_order_picking()

    # Override l10n_pt.mixin
    @api.depends('country_code', 'name', 'session_id.config_id.sequence_id.prefix')
    def _compute_l10n_pt_document_number(self):
        for order in self.filtered(lambda o: (
            o.country_code == 'PT'
            and o.name
            and o.session_id.config_id.sequence_id.prefix
            and o.date_order
            and o.state in ['paid', 'done', 'invoiced']
            and not o.l10n_pt_document_number
        )):
            seq_info = self._l10n_pt_get_sanitized_sequence_info(order.session_id.config_id.sequence_id.prefix, name=order.name)
            order.l10n_pt_document_number = f'{order._name} {seq_info}'

    @api.depends('country_code', 'state', 'date_order', 'l10n_pt_document_number')
    def _compute_blockchain_must_hash(self):
        super()._compute_blockchain_must_hash()
        for order in self:
            order.blockchain_must_hash = (
                order.blockchain_must_hash
                or order.blockchain_secure_sequence_number
                or order.l10n_pt_document_number
            )

    def _compute_blockchain_inalterable_hash(self):
        """
        We need an optimization for Portugal where the hash is only computed
        when we actually need it (printing of a pos order or the integrity report).
        This is because in Portugal's case, the hash is computed by Odoo's IAP
        service which needs an RPC call that might be slow.
        """
        super(PosOrder, self.filtered(lambda o: o.company_id.country_id.code != 'PT'))._compute_blockchain_inalterable_hash()
        if self._context.get('l10n_pt_force_compute_signature'):
            super(PosOrder, self.filtered(lambda o: o.company_id.country_id.code == 'PT'))._l10n_pt_compute_blockchain_inalterable_hash()

    def _get_blockchain_inalterable_hash_fields(self):
        if self.company_id.country_id.code != 'PT':
            return super()._get_blockchain_inalterable_hash_fields()
        return ['date_order', 'create_date', 'l10n_pt_document_number', 'amount_total', 'name']

    def _get_blockchain_sorting_keys(self):
        if self.company_id.country_id.code != 'PT':
            return super()._get_blockchain_sorting_keys()
        return ['date_order', 'id']

    def _get_blockchain_secure_sequence(self):
        self.ensure_one()
        if self.company_id.country_id.code != 'PT':
            return super()._get_blockchain_secure_sequence()
        self.company_id._l10n_pt_create_pos_secure_sequence(self.company_id)
        return self.company_id.l10n_pt_pos_secure_sequence_id

    def _get_blockchain_previous_record_domain(self):
        if self.company_id.country_id.code != 'PT':
            return super()._get_blockchain_previous_record_domain()
        return [
            ('state', 'in', ['paid', 'done', 'invoiced']),
            ('company_id', '=', self.company_id.id),
            ('id', '!=', self.id),
            ('blockchain_secure_sequence_number', '<', self.blockchain_secure_sequence_number),
            ('blockchain_secure_sequence_number', '!=', 0)
        ]

    def _get_blockchain_record_hash_string(self, previous_hash=None):
        self.ensure_one()
        if self.company_id.country_id.code != 'PT':
            return super()._get_blockchain_record_hash_string(previous_hash)
        return self._l10n_pt_get_blockchain_record_hash_string(previous_hash)

    @api.model
    def _l10n_pt_pos_cron_compute_missing_hashes(self):
        companies = self.env['res.company'].search([]).filtered(lambda c: c.country_id.code == 'PT')
        for company in companies:
            self.env['pos.order'].l10n_pt_compute_missing_hashes(company.id)


class PosOrderLine(models.Model):
    _name = 'pos.order.line'
    _inherit = ['pos.order.line', 'sub.blockchain.mixin']

    def _get_sub_blockchain_inalterable_hash_fields(self):
        if self.company_id.country_id.code != 'PT':
            return super()._get_sub_blockchain_inalterable_hash_fields()
        return []
