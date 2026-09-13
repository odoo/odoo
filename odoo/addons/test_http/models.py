from odoo import api, fields, models
from odoo.http import request

MILKY_WAY_REGIONS = ["P3X", "P4X", "P2X", "P5C"]
PEGASUS_REGIONS = ["M4R", "P3Y", "M6R"]


class Test_HttpStargate(models.Model):
    _name = "test_http.stargate"
    _description = "Stargate"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity"]

    name = fields.Char(
        compute="_compute_name",
        store=True,
        readonly=False,
        required=True,
    )
    address = fields.Char(required=True)
    sgc_designation = fields.Char(
        compute="_compute_sgc_designation",
        store=True,
    )
    galaxy_id = fields.Many2one(
        comodel_name="test_http.galaxy",
        required=True,
    )
    has_galaxy_crystal = fields.Boolean(
        compute="_compute_has_galaxy_crystal",
        store=True,
        readonly=False,
    )
    glyph_attach = fields.Image(attachment=True)
    glyph_inline = fields.Image(attachment=False)
    glyph_related = fields.Image(
        related="glyph_attach",
        string="Glyph 128",
        max_width=128,
        max_height=128,
        store=True,
    )
    glyph_compute = fields.Image(compute="_compute_glyph_compute")
    galaxy_picture = fields.Image(
        related="galaxy_id.picture",
        store=False,
    )
    availability = fields.Float(
        default=0.99,
        aggregator="avg",
    )
    last_use_date = fields.Date()

    _address_length = models.Constraint(
        "CHECK(LENGTH(address) = 6)",
        "Local addresses have 6 glyphs",
    )

    @api.depends("galaxy_id")
    def _compute_has_galaxy_crystal(self):
        milky_way = self.env.ref("test_http.milky_way")
        for gate in self:
            gate.has_galaxy_crystal = gate.galaxy_id == milky_way

    @api.depends("sgc_designation")
    def _compute_name(self):
        for gate in self:
            if not gate.name:
                gate.name = gate.sgc_designation

    @api.depends("address")
    def _compute_sgc_designation(self):
        for gate in self:
            if gate.galaxy_id.name not in ("Milky Way", "Pegasus"):
                gate.sgc_designation = False
                continue

            region_part = (
                PEGASUS_REGIONS[gate.id % len(PEGASUS_REGIONS)]
                if gate.galaxy_id.name == "Pegasus"
                else MILKY_WAY_REGIONS[gate.id % len(MILKY_WAY_REGIONS)]
            )
            local_part = str(int.from_bytes(gate.address.encode(), "big"))[:3]
            gate.sgc_designation = f"{region_part}-{local_part}"

    @api.depends("glyph_attach")
    def _compute_glyph_compute(self):
        for gate in self:
            gate.glyph_compute = gate.glyph_attach


class Test_HttpGalaxy(models.Model):
    _name = "test_http.galaxy"
    _description = "Galaxy"

    name = fields.Char(
        required=True,
        help="The galaxy common name.",
    )
    translated_name = fields.Char(translate=True)
    picture = fields.Image(
        attachment=True,
        groups="base.group_user",
    )
    stargate_ids = fields.One2many(
        comodel_name="test_http.stargate",
        inverse_name="galaxy_id",
        string="stargates",
    )

    @api.model
    def render(self, galaxy_id):
        return self.env["ir.qweb"]._render(
            "test_http.tmpl_galaxy", {"galaxy": self.browse([galaxy_id])}
        )


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _pre_dispatch(cls, rule, args):
        if request.httprequest.headers.get("X-Test-Reroute"):
            request.reroute(request.httprequest.path)
        super()._pre_dispatch(rule, args)
