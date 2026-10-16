from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import convert


class FidelityProgram(models.Model):
    """
    TODO: Translate in english.

    Programme possible:
    - Carte de fidelité, recolte de points pour ensuite pouvoir les dépenser dans les récompenses liées.
    - Promotion activable sur la commande courante, si les règles sont respectées, la promotion est appliquée.
    - Promotion activable sur la commande suivante, si les règles sont respectées, un coupon est généré pour la prochaine commande.

    Conditions d'activation (commulables):
    Chaque conditions remplie attribue des points sur le modèle "fidelity.balance", ce dernier est lié à une carte "fidelity.card".
    - Basée sur les produits achetés, sélectionnable via les catégories, les tags ou les produits eux-mêmes.
        => Cette règle peut être combinée avec une quantité minimale achetée.
    - Basée sur le montant total de la commande.

    Récompenses possibles:
    """

    _name = 'fidelity.program'
    _description = "Fidelity Program"

    name = fields.Char(string="Program Name", translate=True, required=True)
    sequence = fields.Integer(default=1)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(string="Company", comodel_name='res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string="Currency", related='company_id.currency_id')
    pricelist_ids = fields.Many2many('product.pricelist', string="Pricelists", domain="[('currency_id', '=', currency_id)]")
    balance_ids = fields.One2many('fidelity.balance', 'program_id', string="Fidelity Balances", readonly=True)
    card_ids = fields.Many2many('fidelity.card', compute='_compute_card_ids', readonly=True, string="Fidelity Cards")
    nb_cards = fields.Integer(string="Cards", compute='_compute_card_ids', readonly=True)

    # Configuration
    rule_ids = fields.One2many('fidelity.rule', 'program_id', string="Fidelity rules")
    reward_ids = fields.One2many('fidelity.reward', 'program_id', string="Fidelity rewards")
    type = fields.Selection(selection=[
            ('fidelity_card', "Fidelity Cards"),
            ('order_promotion', "Order Promotions"),
            ('next_order_promotion', "Next Order Promotions"),
        ],
        required=True,
        default='order_promotion',
    )
    trigger = fields.Selection(selection=[
            ('manual', 'Manual'),
            ('automatic', 'Automatic'),
        ],
        string="Trigger",
        required=True,
        default='manual',
    )

    # Restrictions
    start_date = fields.Date(string="Start Date", help="The start date is included in the validity period of this program")
    end_date = fields.Date(string="End date", help="The end date is included in the validity period of this program")
    point_unit = fields.Char("Point Unit", default="pt", help="The unit used to display points (e.g., pt, pts, stars).")
    limit_usage = fields.Boolean(string="Usage Limit", help="Maximum number of times this program can be used.")
    limit_usage_maximum = fields.Integer("Maximum Usage", help="The program cannot be used more than this number of times in total across all customers.")
    limit_usage_remaining = fields.Integer("Remaining Usages", compute='_compute_limit_usage_remaining', store=True, readonly=True)
    trigger_product_ids = fields.Many2many(related='rule_ids.product_ids', readonly=False)

    @api.depends('limit_usage', 'limit_usage_maximum', 'balance_ids', 'balance_ids.transaction_ids')
    def _compute_limit_usage_remaining(self):
        for program in self:
            usage = program.balance_ids.transaction_ids.filtered(lambda t: t.state == 'done' and t.reward_id in program.reward_ids)
            program.limit_usage_remaining = program.limit_usage_maximum - len(usage)

    @api.depends('balance_ids', 'balance_ids.card_id')
    def _compute_card_ids(self):
        for program in self:
            cards = program.balance_ids.mapped('card_id')
            program.card_ids = cards
            program.nb_cards = len(cards)

    @api.constrains('type')
    def _check_type(self):
        for program in self:
            if len(program.balance_ids) > 0:
                raise UserError(_("You cannot change the type of a program that already has transactions."))

    @api.constrains('limit_usage', 'limit_usage_maximum')
    def _check_limit_usage(self):
        for program in self:
            if program.limit_usage and program.limit_usage_maximum <= 0:
                raise UserError(_("If you set a usage limit, the maximum usage must be greater than 0."))

    @api.constrains('trigger', 'type')
    def _check_trigger_type(self):
        for program in self:
            if program.type == 'fidelity_card' and program.trigger != 'manual':
                raise UserError(_("Fidelity Card programs can only have 'Manual' as trigger."))

    @api.constrains('currency_id', 'pricelist_ids')
    def _check_pricelist_currency(self):
        for program in self:
            if any(pricelist.currency_id != program.currency_id for pricelist in program.pricelist_ids):
                raise UserError(_(
                    "The loyalty program's currency must be the same as all it's pricelists ones.",
                ))

    @api.constrains('start_date', 'end_date')
    def _check_start_date_end_date(self):
        if any(p.end_date and p.start_date and p.start_date > p.end_date for p in self):
            raise UserError(_(
                "The validity period's start date must be anterior or equal to its end date.",
            ))

    @api.model
    def get_fidelity_program_list_view_state(self):
        has_records = self.search_count([], limit=1) > 0
        return {
            'has_records': has_records,
        }

    @api.model
    def create_default_fidelity_program(self, program_type):
        loyalty_product_example = self.env.ref("fidelity.fidelity_product_example_1", raise_if_not_found=False)
        if not loyalty_product_example:
            convert.convert_file(
                self.env,
                'fidelity',
                'data/fidelity_program_base_data.xml',
                idref=None,
                mode='init',
                noupdate=True,
            )

        program_mapping = {
            'buy_x_get_y': 'data/fidelity_program_buy_x_get_y.xml',
            'fidelity_points': 'data/fidelity_program_fidelity_points.xml',
            'promotion': 'data/fidelity_program_next_order_coupon.xml',
        }

        target_file = program_mapping.get(program_type)
        if not target_file:
            raise UserError(_("The selected program type does not have associated demo data."))

        convert.convert_file(
            self.env,
            'fidelity',
            target_file,
            idref=None,
            mode='init',
            noupdate=True,
        )

    def action_open_fidelity_cards(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('fidelity.fidelity_card_action')
        action['domain'] = [('id', 'in', self.balance_ids.card_id.ids)]
        return action

    def meet_any_rule(self, order):
        """
        Since fidelity must works with Point of Sale and Sales, we need to
        have a common method to check if an order meet at least one rule of
        the fidelity program.

        This method is intended to be overridden in order to provide the
        actual implementation depending on the module (point_of_sale or sale).
        """
        pass

    def get_order_partner(self, order):
        """
        Since fidelity must works with Point of Sale and Sales, we need to
        have a common method to check if an order meet at least one rule of
        the fidelity program.

        This method is intended to be overridden in order to provide the
        actual implementation depending on the module (point_of_sale or sale).
        """
        pass

    def upsert_new_fidelity_card(self, partner_id):
        self.ensure_one()
        # Check if partner already has a fidelity card, if not create one
        card = self.env['fidelity.card'].search([('partner_id', '=', partner_id.id)])
        if not card.exists():
            card = self.env['fidelity.card'].create({
                'partner_id': partner_id.id,
            })

        # Check if a balance already exists for this partner and program, if not create it
        balance = self.env['fidelity.balance'].search([('card_id', '=', card.id)])
        if not balance.exists():
            self.env['fidelity.balance'].create({
                'partner_id': partner_id.id,
                'program_id': self.id,
                'card_id': card.id,
            })

        return card
