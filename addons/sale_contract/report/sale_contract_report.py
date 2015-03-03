from openerp import tools
from openerp import fields, models


class sale_contract_report(models.Model):
    _name = "sale.contract.report"
    _description = "Subscription Statistics"
    _auto = False

    date_start = fields.Date('Date Start', readonly=True)
    date_end = fields.Date('Date End', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    product_uom = fields.Many2one('product.uom', 'Unit of Measure', readonly=True)
    recurring_price = fields.Float('Recurring price(per period)', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    manager_id = fields.Many2one('res.users', 'Sales Rep', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    state = fields.Selection([('template', 'Template'),
                              ('draft', 'New'),
                              ('open', 'In Progress'),
                              ('pending', 'To Renew'),
                              ('close', 'Closed'),
                              ('cancelled', 'Cancelled')], readonly=True)
    categ_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
    parent_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
    template_id = fields.Many2one('account.analytic.account', 'Subscription Template', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', readonly=True)
    country_id = fields.Many2one('res.country', 'Country', readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', 'Comercial Partner', readonly=True)

    def _select(self):
        select_str = """
             SELECT min(l.id) as id,
                    l.product_id as product_id,
                    l.uom_id as product_uom,
                    l.analytic_account_id,
                    (l.price_unit * l.quantity) as recurring_price,
                    a.date_start as date_start,
                    a.date as date_end,
                    a.partner_id as partner_id,
                    a.manager_id as manager_id,
                    a.company_id as company_id,
                    a.state,
                    a.template_id as template_id,
                    t.categ_id as categ_id,
                    a.pricelist_id as pricelist_id,
                    a.parent_id as parent_id,
                    p.product_tmpl_id,
                    partner.country_id as country_id,
                    partner.commercial_partner_id as commercial_partner_id
        """
        return select_str

    def _from(self):
        from_str = """
                account_analytic_invoice_line l
                      join account_analytic_account a on (l.analytic_account_id=a.id) and (a.contract_type='subscription') and (a.type!='template')
                      join res_partner partner on a.partner_id = partner.id
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                    left join product_uom u on (u.id=l.uom_id)
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY l.product_id,
                    l.uom_id,
                    t.categ_id,
                    l.analytic_account_id,
                    a.date_start,
                    a.date,
                    a.partner_id,
                    a.manager_id,
                    recurring_price,
                    a.company_id,
                    a.state,
                    a.template_id,
                    a.pricelist_id,
                    a.parent_id,
                    p.product_tmpl_id,
                    partner.country_id,
                    partner.commercial_partner_id
        """
        return group_by_str

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))