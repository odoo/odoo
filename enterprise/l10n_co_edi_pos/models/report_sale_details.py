from odoo import models, api
from odoo.tools import SQL


class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
        # EXTEND point_of_sale

        def get_name_for(order):
            return order.account_move.name if order.to_invoice else order.name

        data = super().get_sale_details(date_start, date_stop, config_ids, session_ids)

        data['l10n_co_edi_pos_enable'] = self.env.company.l10n_co_edi_pos_dian_enabled

        if data['l10n_co_edi_pos_enable']:
            if not session_ids:
                date_start, date_stop = self._get_date_start_and_date_stop(date_start, date_stop)

            domain = self._get_domain(date_start, date_stop, config_ids, session_ids, **kwargs)
            orders = self.env['pos.order'].search(domain)

            payment_options = None
            if order_ids := tuple(orders.ids):
                query = SQL(
                    """
                        SELECT %(option_name)s as name,
                               COUNT(copo.code) transaction_count,
                               SUM(pp.amount) total
                          FROM pos_payment pp
                          JOIN pos_payment_method ppm ON ppm.id = pp.payment_method_id
                          JOIN l10n_co_edi_payment_option copo ON copo.id = ppm.l10n_co_edi_pos_payment_option_id
                         WHERE pp.pos_order_id IN %(pos_order_ids)s
                         GROUP BY ppm.id, pp.session_id, copo.id, ppm.journal_id
                    """,
                    option_name=self.env['l10n_co_edi.payment.option']._field_to_sql('copo', 'name'),
                    pos_order_ids=order_ids,
                )
                self.env.cr.execute(query)
                payment_options = self.env.cr.dictfetchall()

            data['l10n_co_edi_pos_payment_options'] = payment_options or []
            serial_numbers = (self.env['pos.config'].browse(config_ids).exists() or orders.config_id).mapped('l10n_co_edi_pos_serial_number')
            serial_numbers = [sn if sn else "" for sn in serial_numbers]
            data['l10n_co_edi_pos_serial_number'] = ", ".join(serial_numbers)

            if orders:
                data['l10n_co_edi_pos_start_pos_order_number'] = get_name_for(orders[-1])
                data['l10n_co_edi_pos_end_pos_order_number'] = get_name_for(orders[0])
            else:
                data['l10n_co_edi_pos_start_pos_order_number'] = ""
                data['l10n_co_edi_pos_end_pos_order_number'] = ""

        return data
