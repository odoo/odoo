
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

class wizard_valuation_history(osv.osv_memory):

    _name = 'wizard.valuation.history'
    _description = 'Wizard that opens the stock valuation history table'
    _columns = {
        'choose_date': fields.boolean('Choose a Particular Date'),
        'date': fields.datetime('Date', required=True),
    }

    _defaults = {
        'choose_date': False,
        'date': fields.datetime.now,
    }

    def open_table(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        ctx = context.copy()
        ctx['history_date'] = data['date']
        ctx['search_default_group_by_product'] = True
        ctx['search_default_group_by_location'] = True
        return {
            'domain': "[('date', '<=', '" + data['date'] + "')]",
            'name': _('Stock Value At Date'),
            'view_type': 'form',
            'view_mode': 'tree,graph',
            'res_model': 'stock.history',
            'type': 'ir.actions.act_window',
            'context': ctx,
        }


class stock_history(osv.osv):
    _name = 'stock.history'
    _auto = False
    _order = 'date asc'

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        res = super(stock_history, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        if context is None:
            context = {}
        date = context.get('history_date')
        prod_dict = {}
        if 'inventory_value' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(cr, uid, line['__domain'], context=context)
                    inv_value = 0.0
                    product_tmpl_obj = self.pool.get("product.template")
                    lines_rec = self.browse(cr, uid, lines, context=context)
                    for line_rec in lines_rec:
                        if line_rec.product_id.cost_method == 'real':
                            price = line_rec.price_unit_on_quant
                        else:
                            if not line_rec.product_id.id in prod_dict:
                                prod_dict[line_rec.product_id.id] = product_tmpl_obj.get_history_price(cr, uid, line_rec.product_id.product_tmpl_id.id, line_rec.company_id.id, date=date, context=context)
                            price = prod_dict[line_rec.product_id.id]
                        inv_value += price * line_rec.quantity
                    line['inventory_value'] = inv_value
        return res

    def _get_inventory_value(self, cr, uid, ids, name, attr, context=None):
        if context is None:
            context = {}
        date = context.get('history_date')
        product_tmpl_obj = self.pool.get("product.template")
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.product_id.cost_method == 'real':
                res[line.id] = line.quantity * line.price_unit_on_quant
            else:
                res[line.id] = line.quantity * product_tmpl_obj.get_history_price(cr, uid, line.product_id.product_tmpl_id.id, line.company_id.id, date=date, context=context)
        return res

    _columns = {
        'move_id': fields.many2one('stock.move', 'Stock Move', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'company_id': fields.many2one('res.company', 'Company'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_categ_id': fields.many2one('product.category', 'Product Category', required=True),
        'quantity': fields.integer('Product Quantity'),
        'date': fields.datetime('Operation Date'),
        'price_unit_on_quant': fields.float('Value'),
        'inventory_value': fields.function(_get_inventory_value, string="Inventory Value", type='float', readonly=True),
        'source': fields.char('Source')
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'stock_history')
        cr.execute("""
            CREATE OR REPLACE VIEW stock_history AS (
              SELECT MIN(id) as id,
                move_id,
                location_id,
                company_id,
                product_id,
                product_categ_id,
                SUM(quantity) as quantity,
                date,
                price_unit_on_quant,
                source
                FROM
                ((SELECT
                    stock_move.id::text || '-' || quant.id::text AS id,
                    quant.id AS quant_id,
                    stock_move.id AS move_id,
                    dest_location.id AS location_id,
                    dest_location.company_id AS company_id,
                    stock_move.product_id AS product_id,
                    product_template.categ_id AS product_categ_id,
                    quant.qty AS quantity,
                    stock_move.date AS date,
                    quant.cost as price_unit_on_quant,
                    stock_move.origin AS source
                FROM
                    stock_quant as quant, stock_quant_move_rel, stock_move
                LEFT JOIN
                   stock_location dest_location ON stock_move.location_dest_id = dest_location.id
                LEFT JOIN
                    stock_location source_location ON stock_move.location_id = source_location.id
                LEFT JOIN
                    product_product ON product_product.id = stock_move.product_id
                LEFT JOIN
                    product_template ON product_template.id = product_product.product_tmpl_id
                WHERE stock_move.state = 'done' AND dest_location.usage in ('internal', 'transit') AND stock_quant_move_rel.quant_id = quant.id
                AND stock_quant_move_rel.move_id = stock_move.id AND ((source_location.company_id is null and dest_location.company_id is not null) or
                (source_location.company_id is not null and dest_location.company_id is null) or source_location.company_id != dest_location.company_id)
                ) UNION
                (SELECT
                    '-' || stock_move.id::text || '-' || quant.id::text AS id,
                    quant.id AS quant_id,
                    stock_move.id AS move_id,
                    source_location.id AS location_id,
                    source_location.company_id AS company_id,
                    stock_move.product_id AS product_id,
                    product_template.categ_id AS product_categ_id,
                    - quant.qty AS quantity,
                    stock_move.date AS date,
                    quant.cost as price_unit_on_quant,
                    stock_move.origin AS source
                FROM
                    stock_quant as quant, stock_quant_move_rel, stock_move
                LEFT JOIN
                    stock_location source_location ON stock_move.location_id = source_location.id
                LEFT JOIN
                    stock_location dest_location ON stock_move.location_dest_id = dest_location.id
                LEFT JOIN
                    product_product ON product_product.id = stock_move.product_id
                LEFT JOIN
                    product_template ON product_template.id = product_product.product_tmpl_id
                WHERE stock_move.state = 'done' AND source_location.usage in ('internal', 'transit') AND stock_quant_move_rel.quant_id = quant.id
                AND stock_quant_move_rel.move_id = stock_move.id AND ((dest_location.company_id is null and source_location.company_id is not null) or
                (dest_location.company_id is not null and source_location.company_id is null) or dest_location.company_id != source_location.company_id)
                ))
                AS foo
                GROUP BY move_id, location_id, company_id, product_id, product_categ_id, date, price_unit_on_quant, source
            )""")
