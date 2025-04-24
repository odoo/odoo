# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import AND, OR


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_analytic_distribution(self):
        # when a project creates an aml, it adds an analytic account to it. the following filter is to save this
        # analytic account from being overridden by analytic default rules and lack thereof
        project_amls = self.filtered(lambda aml: aml.analytic_distribution and any(aml.sale_line_ids.project_id))
        super(AccountMoveLine, self - project_amls)._compute_analytic_distribution()
        project_id = self._context.get('project_id', False)
        if project_id:
            project = self.env['project.project'].browse(project_id)
            lines = self.filtered(lambda line: line.account_type not in ['asset_receivable', 'liability_payable'])
            lines.analytic_distribution = project._get_analytic_distribution()

    def _get_so_mapping_domain(self):
        return OR([
            OR([
                AND([
                    [(self.env['account.analytic.account'].browse(int(account_id)).root_plan_id._column_name(), "=", int(account_id))]
                    for account_id in key.split(",")
                ])
                for key in line.analytic_distribution or []
            ])
            for line in self
        ])

    def _get_so_mapping_from_project(self):
        """ Get the mapping of move.line with the sale.order record on which its analytic entries should be reinvoiced.
            A sale.order matches a move.line if the sale.order's project contains all the same analytic accounts
            as the ones in the distribution of the move.line.
            :return a dict where key is the move line id, and value is sale.order record (or None).
        """
        mapping = {}
        projects = self.env['project.project'].search(domain=self._get_so_mapping_domain())
        orders_per_project = dict(self.env['sale.order']._read_group(
            domain=[('project_id', 'in', projects.ids)],
            groupby=['project_id'],
            aggregates=['id:recordset']
        ))
        project_per_accounts = {
            next(iter(project._get_analytic_distribution())): project
            for project in projects
        }

        for move_line in self:
            analytic_distribution = move_line.analytic_distribution
            if not analytic_distribution:
                continue

            for accounts in analytic_distribution:
                project = project_per_accounts.get(accounts)
            if not project:
                continue

            orders = orders_per_project.get(project)
            if not orders:
                continue
            orders = orders.sorted('create_date')
            in_sale_state_orders = orders.filtered(lambda s: s.state == 'sale')

            mapping[move_line.id] = in_sale_state_orders[0] if in_sale_state_orders else orders[0]

        # map the move line index with the SO on which it needs to be reinvoiced. May be empty if no SO found
        return mapping

    def _sale_determine_order(self):
        mapping_from_invoice = super()._sale_determine_order()
        mapping_from_invoice.update(self._get_so_mapping_from_project())
        return mapping_from_invoice
