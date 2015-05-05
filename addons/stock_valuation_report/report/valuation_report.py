from openerp.osv import osv
from openerp.report import report_sxw


class valuation_report(report_sxw.rml_parse):

    def _get_real(self, form):
        date = form['date']
        category = form['product_category_id'][0]
        liste = self.pool['product.product'].search(self.cr, self.uid, [('product_tmpl_id.cost_method', '=', 'real'),
                                                                        ('product_tmpl_id.categ_id', 'child_of', category)])
        res = []
        if liste:
            self.cr.execute("select id, name_template, sum(qty), sum(qty * cost) \
                                from\
                                ((select p.id, p.name_template, sq.qty, sq.cost\
                                from stock_move sm\
                                inner join product_product p on p.id = sm.product_id\
                                inner join product_price_history pph on p.product_tmpl_id = pph.product_template_id\
                                inner join stock_location destination on sm.location_dest_id = destination.id\
                                inner join stock_location source on sm.location_id = source.id\
                                inner join stock_quant_move_rel sqmr on sm.id = sqmr.move_id\
                                inner join stock_quant sq on sqmr.quant_id = sq.id\
                                where sm.product_id in %s and sm.company_id = pph.company_id and pph.datetime <= %s \
                                and sq.qty>0 and destination.usage in ('internal', 'transit') and source.usage not in ('internal'))\
                                union\
                                (select p.id, p.name_template, -sq.qty, sq.cost\
                                from stock_move sm\
                                inner join product_product p on p.id = sm.product_id\
                                inner join product_price_history pph on p.product_tmpl_id = pph.product_template_id\
                                inner join stock_location destination on sm.location_dest_id = destination.id\
                                inner join stock_location source on sm.location_id = source.id\
                                inner join stock_quant_move_rel sqmr on sm.id = sqmr.move_id\
                                inner join stock_quant sq on sqmr.quant_id = sq.id\
                                where sm.product_id in %s and sm.company_id = pph.company_id and pph.datetime <= %s \
                                and sq.qty>0 and destination.usage not in ('internal') and source.usage in ('internal', 'transit')))\
                                as foo \
                                group by p.id\
                                ", (tuple(liste), date, tuple(liste), date))
            res = [{'name': t[1], 'qty': t[2], 'value': t[3]} for t in self.cr.fetchall()]
        return res

    def _get_standard_average(self, form):
        date = form['date']
        category = form['product_category_id'][0]
        liste = self.pool['product.product'].search(self.cr, self.uid, [('product_tmpl_id.cost_method', 'in', ('standard', 'average')),
                                                                        ('product_tmpl_id.categ_id', 'child_of', category)])
        res = []
        if liste:
            self.cr.execute("select p.id, p.name_template, sum(sm.product_qty), sum(sm.product_qty * pph.cost) \
                                from stock_move sm\
                                inner join product_product p on p.id = sm.product_id\
                                inner join product_price_history pph on p.product_tmpl_id = pph.product_template_id\
                                where product_id in %s and sm.company_id = pph.company_id and pph.datetime <= %s group by p.id\
                                ", (tuple(liste), date))
            res = [{'name': t[1], 'qty': t[2], 'value': t[3]} for t in self.cr.fetchall()]
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
