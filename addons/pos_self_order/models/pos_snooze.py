# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import api, fields, models
from odoo.fields import Domain


class PosSnooze(models.Model):
    _inherit = 'pos.snooze'

    type = fields.Selection(selection_add=[('self-ordering', 'Self Order Service')], ondelete={'self-ordering': 'cascade'})

    @api.model
    def _sync_snoozes(self, config, updated_records=None, deleted_record_ids=None):
        if not config.current_session_id:
            return

        super()._sync_snoozes(config, updated_records, deleted_record_ids)
        payload = {
            'deleted_ids': deleted_record_ids if deleted_record_ids else [],
            'records': self._load_pos_self_data_read(updated_records, config) if updated_records else [],
        }
        config._notify('SNOOZE_CHANGED', payload)

    @api.model_create_multi
    def create(self, vals_list):
        propagated_vals = []
        target_configs_cache = {}

        for vals in vals_list:
            if vals.get('type', 'product') != 'product' or not vals.get('product_template_id'):
                continue

            config_id = vals.get('pos_config_id')
            if not config_id:
                continue

            if config_id not in target_configs_cache:
                config = self.env['pos.config'].browse(config_id)
                kiosks = self.env['pos.config'].search([('company_id', '=', config.company_id.id), ('self_ordering_mode', '=', 'kiosk')])
                target_configs_cache[config_id] = (kiosks - config).ids

            propagated_vals.extend([{**vals, 'pos_config_id': target_id} for target_id in target_configs_cache[config_id]])

        return super().create(vals_list + propagated_vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_kiosk_snoozes(self):
        if self.env.context.get('skip_snooze_propagation'):
            return

        product_snoozes = self.filtered(lambda s: s.type == 'product' and s.product_template_id)
        if not product_snoozes:
            return

        products_by_company = defaultdict(set)
        for snooze in product_snoozes:
            products_by_company[snooze.pos_config_id.company_id.id].add(snooze.product_template_id.id)

        domains = [
            [
                ('pos_config_id.company_id', '=', company_id),
                ('product_template_id', 'in', product_tmpl_ids),
            ]
            for company_id, product_tmpl_ids in products_by_company.items()
        ]

        linked = self.search(
            Domain.OR(domains) & Domain([
                ('pos_config_id.self_ordering_mode', '=', 'kiosk'),
                ('type', '=', 'product'),
                ('id', 'not in', self.ids),
            ])
        )

        if linked:
            linked.with_context(skip_snooze_propagation=True).unlink()
