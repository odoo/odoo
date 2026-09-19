from odoo import _, fields, models, tools
from odoo.db.schema import drop_view_if_exists


class LunchCashmoveReport(models.Model):
    _name = "lunch.cashmove.report"
    _description = "Cashmoves report"
    _auto = False
    _order = "date desc"

    id = fields.Id(string="ID")
    amount = fields.Float()
    date = fields.Date()
    currency_id = fields.Many2one(comodel_name="res.currency")
    user_id = fields.Many2one(comodel_name="res.users")
    description = fields.Text()

    def _compute_display_name(self):
        for cashmove in self:
            cashmove.display_name = "{} {}".format(
                _("Lunch Cashmove"), "#%d" % cashmove.id
            )

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute(
            """
            CREATE or REPLACE view %s as (
                SELECT
                    lc.id as id,
                    lc.amount as amount,
                    lc.date as date,
                    lc.currency_id as currency_id,
                    lc.user_id as user_id,
                    lc.description as description
                FROM lunch_cashmove lc
                UNION ALL
                SELECT
                    -lol.id as id,
                    -lol.price as amount,
                    lol.date as date,
                    company.currency_id as currency_id,
                    lol.user_id as user_id,
                    format('Order: %%s x %%s %%s', lol.quantity::text, lp.name->>'en_US', lol.display_toppings) as description
                FROM lunch_order lol
                JOIN lunch_product lp ON lp.id = lol.product_id
                LEFT JOIN res_company company ON company.id = lol.company_id
                WHERE
                    lol.state in ('ordered', 'confirmed')
                    AND lol.active = True
            );
        """
            % self._table
        )
