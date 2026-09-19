import ast
import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools.misc import str2bool


class LoyaltyReward(models.Model):
    _name = "loyalty.reward"
    _description = "Loyalty Reward"
    _rec_name = "description"
    _order = "required_points asc"

    # Everything `_get_domain_discount_product` reads, and so every field that
    # invalidates both representations of the discounted products.
    _DISCOUNT_PRODUCT_DEPENDS = (
        "discount_product_ids",
        "discount_product_category_id",
        "discount_product_tag_id",
        "discount_product_domain",
    )

    @api.model
    def default_get(self, fields):
        # Copy the reward defaults of the program type given in the context, if any
        result = super().default_get(fields)
        program_type = self.env.context.get("program_type")
        if program_type:
            defaults = self.env["loyalty.program"]._get_child_default_values(
                program_type, "reward_ids"
            )
            result.update({k: v for k, v in defaults.items() if k in fields})
        return result

    def _selection_discount_modes(self):
        # The value is provided in the loyalty program's view since we may not have a program_id yet
        #  and makes sure to display the currency related to the program instead of the company's.
        symbol = self.env.context.get(
            "currency_symbol", self.env.company.currency_id.symbol
        )
        return [
            ("percent", "%"),
            ("per_order", symbol),
            ("per_point", _("%s per point", symbol)),
        ]

    @api.depends("program_id", "description")
    def _compute_display_name(self):
        for reward in self:
            reward.display_name = f"{reward.program_id.name} - {reward.description}"

    active = fields.Boolean(default=True)
    program_id = fields.Many2one(
        comodel_name="loyalty.program",
        index=True,
        required=True,
        ondelete="cascade",
    )
    program_type = fields.Selection(related="program_id.program_type")
    # Stored for security rules
    company_id = fields.Many2one(
        related="program_id.company_id",
    )
    currency_id = fields.Many2one(related="program_id.currency_id")

    description = fields.Char(
        translate=True,
        compute="_compute_description",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )

    reward_type = fields.Selection(
        selection=[
            ("product", "Free Product"),
            ("discount", "Discount"),
        ],
        default="discount",
        required=True,
    )
    user_has_debug = fields.Boolean(compute="_compute_user_has_debug")

    # Discount rewards
    discount = fields.Float(default=10)
    discount_mode = fields.Selection(
        selection=_selection_discount_modes,
        default="percent",
        required=True,
    )
    discount_applicability = fields.Selection(
        selection=[
            ("order", "Order"),
            ("cheapest", "Cheapest Product"),
            ("specific", "Specific Products"),
        ],
        default="order",
    )
    discount_product_domain = fields.Char(default="[]")
    discount_product_ids = fields.Many2many(
        comodel_name="product.product",
        string="Discounted Products",
    )
    discount_product_category_id = fields.Many2one(
        comodel_name="product.category",
        string="Discounted Prod. Categories",
    )
    discount_product_tag_id = fields.Many2one(
        comodel_name="product.tag",
        string="Discounted Prod. Tag",
    )
    all_discount_product_ids = fields.Many2many(
        comodel_name="product.product",
        compute="_compute_all_discount_product_ids",
    )
    reward_product_domain = fields.Char(
        compute="_compute_reward_product_domain",
        store=False,
    )
    discount_max_amount = fields.Monetary(
        string="Max Discount",
        help="This is the max amount this reward may discount, leave to 0 for no limit.",
    )
    discount_line_product_id = fields.Many2one(
        comodel_name="product.product",
        copy=False,
        ondelete="restrict",
        help="Product used in the sales order to apply the discount. Each reward has its own"
        " product for reporting purpose",
    )
    is_global_discount = fields.Boolean(compute="_compute_is_global_discount")

    # Product rewards
    reward_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        domain=[("type", "!=", "combo")],
    )
    reward_product_tag_id = fields.Many2one(
        comodel_name="product.tag",
        string="Product Tag",
    )
    multi_product = fields.Boolean(compute="_compute_reward_products")
    reward_product_ids = fields.Many2many(
        comodel_name="product.product",
        string="Reward Products",
        compute="_compute_reward_products",
        search="_search_reward_product_ids",
        help="These are the products that can be claimed with this rule.",
    )
    reward_product_qty = fields.Integer(default=1)
    reward_product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        compute="_compute_reward_product_uom_id",
    )

    required_points = fields.Float(
        string="Points needed",
        default=1,
    )
    point_name = fields.Char(
        related="program_id.portal_point_name",
        readonly=True,
    )
    clear_wallet = fields.Boolean(default=False)

    _required_points_positive = models.Constraint(
        "CHECK (required_points > 0)",
        "The required points for a reward must be strictly positive.",
    )
    _product_qty_positive = models.Constraint(
        "CHECK (reward_type != 'product' OR reward_product_qty > 0)",
        "The reward product quantity must be strictly positive.",
    )
    _discount_positive = models.Constraint(
        "CHECK (reward_type != 'discount' OR discount > 0)",
        "The discount must be strictly positive.",
    )

    @api.depends("reward_product_ids.product_tmpl_id.uom_id")
    def _compute_reward_product_uom_id(self):
        # `reward_product_ids` is itself computed from the product, the tag and the
        # reward type: depending on the first two alone left the unit of a reward
        # behind when its type flipped away from 'product'.
        for reward in self:
            reward.reward_product_uom_id = (
                reward.reward_product_ids.product_tmpl_id.uom_id[:1]
            )

    def _find_all_category_children(self, category_id, child_ids):
        if len(category_id.child_id) > 0:
            for child_id in category_id.child_id:
                child_ids.append(child_id.id)
                self._find_all_category_children(child_id, child_ids)
        return child_ids

    def _get_domain_discount_product(self):
        """Return the domain of the products this reward discounts.

        **This domain must stay evaluable by `@web/core/domain`.** It is serialised
        into `reward_product_domain` and re-evaluated in the browser by the PoS
        (`pos_loyalty/static/src/app/services/pos_store.js`), where `child_of` and
        `parent_of` compile to `() => true` -- every product would match. That is why
        the category is expanded into an id list here while `loyalty.rule` states the
        same condition as the server-only `('categ_id', 'child_of', id)`. The two
        methods look like duplicates and are not: unifying them on `child_of` makes
        every PoS discount apply to the whole catalogue.
        """
        self.check_singleton()
        constrains = []
        if self.discount_product_ids:
            constrains.append([("id", "in", self.discount_product_ids.ids)])
        if self.discount_product_category_id:
            product_category_ids = self._find_all_category_children(
                self.discount_product_category_id, []
            )
            product_category_ids.append(self.discount_product_category_id.id)
            constrains.append([("categ_id", "in", product_category_ids)])
        if self.discount_product_tag_id:
            constrains.append(
                [("all_product_tag_ids", "in", self.discount_product_tag_id.id)]
            )
        domain = Domain.OR(constrains) if constrains else Domain.TRUE
        if self.discount_product_domain and self.discount_product_domain != "[]":
            domain &= Domain(ast.literal_eval(self.discount_product_domain))
        return domain

    @api.model
    def _get_domain_active_products(self):
        return [
            "|",
            ("reward_type", "!=", "product"),
            "&",
            ("reward_type", "=", "product"),
            "|",
            "&",
            ("reward_product_tag_id", "=", False),
            ("reward_product_id.active", "=", True),
            "&",
            ("reward_product_tag_id", "!=", False),
            ("reward_product_ids.active", "=", True),
        ]

    def _expands_discount_products(self):
        """Whether the discounted products are resolved here or left to the client.

        Two representations of one thing, and exactly one of them is filled in:
        `all_discount_product_ids` (a server-side search, exact but O(products)) or
        `reward_product_domain` (the domain itself, evaluated by the PoS against the
        products it already holds).
        """
        # The switch is an on/off flag stored as a string. It shipped as the literal
        # "False" while the code compared against "enabled" and defaulted to
        # "enabled" when unset -- so deleting the parameter meant the opposite of
        # what the parameter said. `str2bool` reads the shipped value, the default
        # agrees with it, and "enabled" is still honoured for databases that set it.
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("loyalty.compute_all_discount_product_ids", "")
        )
        return value == "enabled" or str2bool(value, False)

    @api.depends(*_DISCOUNT_PRODUCT_DEPENDS)
    def _compute_reward_product_domain(self):
        # Same dependencies as `_compute_all_discount_product_ids`: both serialise
        # `_get_domain_discount_product`, so both go stale on the same fields. This
        # one used to depend on `discount_product_domain` alone, which left the PoS
        # evaluating a domain that ignored the reward's products, category and tag.
        expands = self._expands_discount_products()
        for reward in self:
            reward.reward_product_domain = (
                "null"
                if expands
                else json.dumps(list(reward._get_domain_discount_product()))
            )

    def _get_discount_products(self):
        """Return the products each of these rewards discounts, in one query.

        One search over the union of the rewards' domains, then each reward's own
        domain applied to the result in memory. Every reward's domain implies the
        union, so nothing a per-reward `search` would have found is missing, and
        `filtered_domain` answers the same as `search` for every operator these
        domains can carry -- `child_of` and a hand-written `discount_product_domain`
        included.

        The trade is one query for the whole set against materialising the union: a
        reward with no constraint contributes `Domain.TRUE` and pulls in the whole
        catalogue. That is the same set `all_discount_product_ids` holds for such a
        reward anyway, and it is loaded once here instead of once per reward.

        :return: the matching products per reward
        :rtype: dict[loyalty.reward, product.product]
        """
        domains = {reward: reward._get_domain_discount_product() for reward in self}
        if not domains:
            return {}
        candidates = self.env["product.product"].search(Domain.OR(domains.values()))
        return {
            reward: candidates.filtered_domain(domain)
            for reward, domain in domains.items()
        }

    @api.depends(*_DISCOUNT_PRODUCT_DEPENDS)
    def _compute_all_discount_product_ids(self):
        if not self._expands_discount_products():
            self.all_discount_product_ids = self.env["product.product"]
            return
        for reward, products in self._get_discount_products().items():
            reward.all_discount_product_ids = products

    @api.depends("reward_product_id", "reward_product_tag_id", "reward_type")
    def _compute_reward_products(self):
        for reward in self:
            products = (
                reward.reward_product_id
                + reward.reward_product_tag_id.product_ids.filtered(
                    lambda product: product.type != "combo"
                )
            )
            reward.multi_product = reward.reward_type == "product" and len(products) > 1
            reward.reward_product_ids = (
                reward.reward_type == "product" and products
            ) or self.env["product.product"]

    def _search_reward_product_ids(self, operator, value):
        # 'any' as well as 'in': the ORM optimizes a relational condition into 'any'
        # (an active_test on the products is enough to produce one), and both operators
        # are delegated unchanged to two relational fields that accept either. The
        # negative forms are not passed through -- the '|' below would have to become a
        # '&' for them.
        if operator not in ("in", "any"):
            return NotImplemented
        return [
            "&",
            ("reward_type", "=", "product"),
            "|",
            ("reward_product_id", operator, value),
            ("reward_product_tag_id.product_ids", operator, value),
        ]

    @api.depends(
        "reward_type",
        "reward_product_id",
        "discount_mode",
        "reward_product_tag_id",
        "discount",
        "currency_id",
        "discount_applicability",
        "all_discount_product_ids",
    )
    def _compute_description(self):
        """Describe each reward, in every language the database has installed.

        `description` is generated *and* translated, and writing a translated field
        under the session's language also writes the source term when the record has
        no source yet. Building the string with `_()` under a Spanish session
        therefore stored Spanish as `en_US` -- so every reward's English description
        was Spanish, and every language without its own translation fell back to it.

        Written once per installed language, source first: writing `en_US` leaves
        existing translations alone, and writing a translation leaves the source
        alone, so each language ends up holding its own current string.
        """
        # Resolved for the whole batch: naming the single product a reward discounts
        # used to cost one `search` per reward. Language-independent, so it is done
        # once outside the loop below.
        products_per_reward = self.filtered(
            lambda reward: (
                reward.program_type not in ("gift_card", "ewallet")
                and reward.reward_type == "discount"
                and reward.discount_applicability == "specific"
            )
        )._get_discount_products()
        # A record being created is written once -- `description` is `precompute`d
        # into the INSERT -- and that single value lands in both the source and the
        # session's language. A new reward therefore gets the source term only,
        # exactly what an English session has always produced, and its translations
        # arrive with the first recompute. It also has to be assigned on `self` and
        # not through another env, or the compute leaves it unset.
        saved = self.browse(self.ids)
        unsaved = self - saved
        for reward, text in zip(
            unsaved,
            unsaved.with_context(lang="en_US")._description_texts(products_per_reward),
            strict=True,
        ):
            reward.description = text
        installed = [code for code, __ in self.env["res.lang"].get_installed()]
        for code in ["en_US", *(code for code in installed if code != "en_US")]:
            translated = saved.with_context(lang=code)
            for reward, text in zip(
                translated,
                translated._description_texts(products_per_reward),
                strict=True,
            ):
                reward.description = text

    def _description_texts(self, products_per_reward):
        """Describe each of these rewards in this recordset's language.

        Returns the texts rather than writing them: which record they are written
        to, and in which env, is what decides whether they land in the source term
        or in a translation.

        :param dict products_per_reward: the products each reward discounts, from
            `_get_discount_products`
        :return: one description per reward, in order
        :rtype: list[str]
        """
        descriptions = []
        for reward in self:
            reward_string = ""
            if reward.program_type == "gift_card":
                reward_string = _("Gift Card")
            elif reward.program_type == "ewallet":
                reward_string = _("eWallet")
            elif reward.reward_type == "product":
                products = reward.reward_product_ids
                if len(products) == 0:
                    reward_string = _("Free Product")
                elif len(products) == 1:
                    reward_string = _(
                        "Free Product - %s",
                        reward.reward_product_id.with_context(
                            display_default_code=False
                        ).display_name,
                    )
                else:
                    reward_string = _(
                        "Free Product - [%s]",
                        ", ".join(
                            products.with_context(display_default_code=False).mapped(
                                "display_name"
                            )
                        ),
                    )
            elif reward.reward_type == "discount":
                format_string = "%(amount)g %(symbol)s"
                if reward.currency_id.position == "before":
                    format_string = "%(symbol)s %(amount)g"
                formatted_amount = format_string % {
                    "amount": reward.discount,
                    "symbol": reward.currency_id.symbol,
                }
                if reward.discount_mode == "percent":
                    reward_string = _("%g%% on ", reward.discount)
                elif reward.discount_mode == "per_point":
                    reward_string = _("%s per point on ", formatted_amount)
                elif reward.discount_mode == "per_order":
                    reward_string = _("%s on ", formatted_amount)
                if reward.discount_applicability == "order":
                    reward_string += _("your order")
                elif reward.discount_applicability == "cheapest":
                    reward_string += _("the cheapest product")
                elif reward.discount_applicability == "specific":
                    product_available = products_per_reward.get(
                        reward, self.env["product.product"]
                    )
                    if len(product_available) == 1:
                        reward_string += product_available.with_context(
                            display_default_code=False
                        ).display_name
                    else:
                        reward_string += _("specific products")
                if reward.discount_max_amount:
                    format_string = "%(amount)g %(symbol)s"
                    if reward.currency_id.position == "before":
                        format_string = "%(symbol)s %(amount)g"
                    formatted_amount = format_string % {
                        "amount": reward.discount_max_amount,
                        "symbol": reward.currency_id.symbol,
                    }
                    reward_string += _(" (Max %s)", formatted_amount)
            descriptions.append(reward_string)
        return descriptions

    @api.depends("reward_type", "discount_applicability", "discount_mode")
    def _compute_is_global_discount(self):
        for reward in self:
            reward.is_global_discount = (
                reward.reward_type == "discount"
                and reward.discount_applicability == "order"
                and reward.discount_mode in ["per_order", "percent"]
            )

    @api.depends_context("uid")
    def _compute_user_has_debug(self):
        # No field dependency: the answer is about the reader, not the record. It
        # used to name one at random, which only widened invalidation.
        self.user_has_debug = self.env.user.has_group("base.group_no_one")

    @api.constrains("reward_product_id")
    def _check_reward_product_id_no_combo(self):
        if any(reward.reward_product_id.type == "combo" for reward in self):
            raise ValidationError(_('A reward product can\'t be of type "combo".'))

    def _create_missing_discount_line_products(self):
        rewards = self.filtered(lambda r: not r.discount_line_product_id)
        products = self.env["product.product"].create(
            rewards._prepare_discount_product_vals()
        )
        for reward, product in zip(rewards, products, strict=True):
            reward.discount_line_product_id = product

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._create_missing_discount_line_products()
        return res

    def write(self, vals):
        res = super().write(vals)
        if "description" in vals:
            self._create_missing_discount_line_products()
            # Keep the name of our discount product up to date
            for reward in self:
                reward.discount_line_product_id.write({"name": reward.description})
        if "active" in vals:
            if vals["active"]:
                self.discount_line_product_id.action_unarchive()
            else:
                self.discount_line_product_id.action_archive()
        return res

    def unlink(self):
        programs = self.program_id
        res = super().unlink()
        # Unlinking rewards does not always trigger the program's constraint
        programs.exists()._check_reward_ids()
        return res

    def _prepare_discount_product_vals(self):
        return [
            {
                "name": reward.description,
                "type": "service",
                "sale_ok": False,
                "purchase_ok": False,
                "lst_price": 0,
            }
            for reward in self
        ]
