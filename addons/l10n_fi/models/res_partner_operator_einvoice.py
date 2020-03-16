# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.osv import expression


class ResPartnerOperatorEinvoice(models.Model):
    _name = "res.partner.operator.einvoice"
    _description = "eInvoice Operator"
    _order = "sequence, id"

    name = fields.Char(
        string="Operator",
        required=True
    )

    active = fields.Boolean(
        default=True
    )

    sequence = fields.Integer(
        "Sequence"
    )

    identifier = fields.Char(
        string="Identifier",
        required=True,
        size=35,
        help="Monetary Institution Identifier (see https://tieke.fi)",
    )

    ttype = fields.Selection(
        [
            ("bank", "Bank with Finvoice brokerage service"),
            ("broker", "Carrier broker"),  # default
        ],
        "Type",
        default="broker",
    )

    _sql_constraints = [
        (
            "operator_identifier_uniq",
            "unique(identifier)",
            '"Identifier" should be unique!',
        ),
    ]

    def name_get(self):
        """
        Overwrite core method to add value of `identifier` ("Identifier")
        field into name of records.
        """
        result = []
        for operator in self:
            name = " - ".join([operator.identifier, operator.name])
            result.append((operator.id, name))
        return result

    @api.model
    def _name_search(
            self, name, args=None, operator="ilike", limit=100,
            name_get_uid=None,
    ):
        """
        Overload core method to add into domain search by `identifier`
        ("Identifier") field

        Args:
         * name(str) - search string
         * args(list of tupples, None) - search domain
         * operator(str) - domain operator for matching `name`, such as
            `"like"` or `"="`.
         * limit(integer, 100) - max number of records to return
         * name_get_uid(integer, None) - ID of dedicated user for the
            `name_get` method to solve some access rights issues

        Returns:
          * list of tuples - (record id, `name_get` of record) of matched
            record
        """
        args = args or []
        domain = []
        if name:
            domain = [
                "|",
                ("identifier", "=ilike", name + "%"),
                ("name", operator, name),
            ]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ["&", "!"] + domain[1:]
        args = expression.AND([domain, args])
        search_results = super(ResPartnerOperatorEinvoice, self)._name_search(
            name=name,
            args=args,
            operator=operator,
            limit=limit,
            name_get_uid=name_get_uid,
        )
        return search_results
