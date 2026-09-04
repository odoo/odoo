# Copyright (C) 2014-Today GRAP (http://www.grap.coop)
# Copyright (C) 2016-Today La Louve (http://www.lalouve.net)
# Copyright 2017 LasLabs Inc.
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models

_GENERATE_TYPE = [
    ("no", "No generation"),
    ("manual", "Base set Manually"),
    ("sequence", "Base managed by Sequence"),
]


class BarcodeRule(models.Model):

    _inherit = "barcode.rule"

    # Column Section
    generate_type = fields.Selection(
        selection=_GENERATE_TYPE,
        required=True,
        default="no",
        help="Allow to generate barcode, including a number"
        "  (a base) in the final barcode.\n\n"
        " - 'Base Set Manually' : User should set manually the value of the"
        " barcode base\n"
        " - 'Base managed by Sequence': System will generate the base"
        " via a sequence",
    )

    generate_model = fields.Selection(
        selection=[],
        help="If 'Generate Type' is set, mention the model related to this rule.",
    )

    padding = fields.Integer(compute="_compute_padding", readonly=True, store=True)

    sequence_id = fields.Many2one(
        string="Generation Sequence", comodel_name="ir.sequence"
    )

    generate_automate = fields.Boolean(
        string="Automatic Generation",
        help="Check this to automatically generate a base and a barcode"
        " if this rule is selected.",
    )

    # Compute Section
    @api.depends("pattern")
    def _compute_padding(self):
        for rule in self:
            rule.padding = rule.pattern.count(".")

    # On Change Section
    @api.onchange("generate_type")
    def onchange_generate_type(self):
        for rule in self:
            if rule.generate_type == "no":
                rule.generate_model = False

    # CRUD
    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.generate_sequence_if_required()
        return res

    def write(self, vals):
        res = super().write(vals)
        self.generate_sequence_if_required()
        return res

    def generate_sequence_if_required(self):
        IrSequence = self.env["ir.sequence"]
        rules = self.filtered(
            lambda x: x.generate_type == "sequence" and not x.sequence_id
        )
        for rule in rules:
            sequence = IrSequence.create(self._prepare_sequence(rule))
            rule.sequence_id = sequence.id

    # Custom Section
    @api.model
    def _prepare_sequence(self, rule):
        return {
            "name": _("Sequence - %s") % rule.name,
            "padding": rule.padding,
        }
