from odoo import api, fields, models


class SifRkaDashboardView(models.TransientModel):
    _inherit = 'sif.rka.dashboard.view'

    display_mode = fields.Selection(
        [('tahunan', 'RKA Tahunan'), ('top3', 'Top 3 Pengeluaran')],
        string='Mode Tampilan',
        default='tahunan'
    )

    def action_switch_to_tahunan(self):
        self.ensure_one()
        self.display_mode = 'tahunan'
        return self._reload_dashboard()

    def action_switch_to_top3(self):
        self.ensure_one()
        self.display_mode = 'top3'
        return self._reload_dashboard()

    def _reload_dashboard(self):
        self.ensure_one()
        tahun = self.tahun or str(fields.Date.today().year)
        all_rka = self.env['sif.rka.budget'].search([
            ('company_id', '=', self.env.company.id),
            ('tahun', '=', tahun),
        ])
        sorted_rka = all_rka.sorted(key=lambda r: r.realisasi, reverse=True)
        top3 = sorted_rka[:3]
        self.write({
            'top3_ids': [(6, 0, top3.ids)],
            'rka_ids': [(6, 0, all_rka.ids)],
        })
        return {
            'type': 'ir.actions.act_window',
            'name': f'Dashboard RKA {tahun}',
            'res_model': 'sif.rka.dashboard.view',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }
