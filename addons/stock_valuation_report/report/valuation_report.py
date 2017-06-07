from openerp.osv import osv
from openerp.report import report_sxw


class valuation_report(report_sxw.rml_parse):

    def _get_real(self, form):
        date = form['date']
        category = form['product_category_id'][0]
        company = form['company_id'][0]
        liste = self.pool['product.product'].search(self.cr, self.uid, [('product_tmpl_id.cost_method', '=', 'real'),
                                                                        ('product_tmpl_id.categ_id', 'child_of', category)])
        res = []
        if liste:
            str_in, str_out, put_params = self._get_location_queries(form)
            query_str = """select id, name_template, sum(qty), sum(qty * cost)
                            from
                            ((select p.id, p.name_template, sq.qty, sq.cost
                            from stock_move sm
                            inner join product_product p on p.id = sm.product_id
                            inner join stock_location destination on sm.location_dest_id = destination.id
                            inner join stock_location source on sm.location_id = source.id
                            inner join stock_quant_move_rel sqmr on sm.id = sqmr.move_id
                            inner join stock_quant sq on sqmr.quant_id = sq.id
                            where sm.product_id in %s and sm.date <= %s and sm.company_id = %s
                             and """
            query_str += str_in
            query_str += """
                    and sm.state='done')
                    union
                    (select p.id, p.name_template, -sq.qty, sq.cost
                    from stock_move sm
                    inner join product_product p on p.id = sm.product_id
                    inner join stock_location destination on sm.location_dest_id = destination.id
                    inner join stock_location source on sm.location_id = source.id
                    inner join stock_quant_move_rel sqmr on sm.id = sqmr.move_id
                    inner join stock_quant sq on sqmr.quant_id = sq.id
                    where sm.product_id in %s and sm.date <= %s and sm.company_id = %s
                     and """
            query_str += str_out
            query_str += """ and sm.state='done'))
                                as foo
                                group by id, name_template
                                """
            params = (tuple(liste), date, company,) + tuple(put_params) + (tuple(liste), date, company,) + tuple(put_params)
            self.cr.execute(query_str, params)
            res = [{'name': t[1], 'qty': t[2], 'value': t[3]} for t in self.cr.fetchall()]
        return res

    def _get_location_queries(self, form):
        method = form['method']
        warehouse = form['warehouse_id'] and form['warehouse_id'][0] or False
        location = form['location_id'] and form['location_id'][0] or False
        put_params = []
        if method in ('internal', 'internal_transit'):
            if method == 'internal':
                type = "('internal')"
            else:
                type = "('internal', 'transit')"
            str_in = "destination.usage in " + type + " and source.usage not in " + type
            str_out = "destination.usage not in " + type + " and source.usage in " + type
        else: # warehouse or location
            if method == 'warehouse':
                location = self.pool['stock.warehouse'].browse(self.cr, self.uid, warehouse).view_location_id.id

            loc = self.pool['stock.location'].browse(self.cr, self.uid, location)
            str_in = " destination.parent_left >= %s and destination.parent_left < %s and not (source.parent_left >= %s and source.parent_left < %s) "
            str_out = " not(destination.parent_left >= %s and destination.parent_left < %s) and (source.parent_left >= %s and source.parent_left < %s) "
            put_params = [loc.parent_left, loc.parent_right, loc.parent_left, loc.parent_right]
        return (str_in, str_out, put_params)


    def _get_standard_average(self, form):
        date = form['date']
        category = form['product_category_id'][0]
        company = form['company_id'][0]

        liste = self.pool['product.product'].search(self.cr, self.uid, [('product_tmpl_id.cost_method', 'in', ('standard', 'average')),
                                                                        ('product_tmpl_id.categ_id', 'child_of', category)])
        res = []
        if liste:
            str_in, str_out, put_params = self._get_location_queries(form)
            query_str = """select product_id, name_template, product_tmpl_id, sum(qty), sum(qty) * pph.cost
                                from
                                ((select p.id as product_id, p.name_template, p.product_tmpl_id, sm.product_qty as qty
                                from stock_move sm
                                inner join product_product p on p.id = sm.product_id
                                inner join stock_location destination on sm.location_dest_id = destination.id
                                inner join stock_location source on sm.location_id = source.id
                                where sm.product_id in %s and sm.date <= %s and sm.company_id = %s and
                                """
            query_str += str_in
            query_str += """
                            and sm.state='done')
                            union
                                (select p.id as product_id, p.name_template, p.product_tmpl_id, -sm.product_qty as qty
                                from stock_move sm
                                inner join product_product p on p.id = sm.product_id
                                inner join stock_location destination on sm.location_dest_id = destination.id
                                inner join stock_location source on sm.location_id = source.id
                                where sm.product_id in %s and sm.date <= %s and sm.company_id = %s and
                                """
            query_str += str_out
            query_str += """
                        and sm.state='done'))
                        as foo, product_price_history pph,
                                 (select product_template_id, max(datetime) as datetime from product_price_history where datetime <= %s and company_id = %s group by product_template_id) as pph_date
                                 where foo.product_tmpl_id = pph_date.product_template_id and pph.datetime = pph_date.datetime and pph.product_template_id = pph_date.product_template_id
                                 group by product_id, name_template, product_tmpl_id, pph.cost
                        """
            params = (tuple(liste), date, company,) + tuple(put_params) + (tuple(liste), date, company,) + tuple(put_params) + (date, company,)
            self.cr.execute(query_str, params)
            res = [{'name': t[1], 'qty': t[3], 'value': t[4]} for t in self.cr.fetchall()]
        return res

    def __init__(self, cr, uid, name, context):
        super(valuation_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'real': self._get_real,
            'standard_average': self._get_standard_average,
        })


class report_valuation_report(osv.AbstractModel):
    _name = 'report.stock_valuation_report.valuation_report'
    _inherit = 'report.abstract_report'
    _template = 'stock_valuation_report.valuation_report'
    _wrapped_report_class = valuation_report
