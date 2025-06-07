# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


MILKY_WAY_REGIONS = ['P3X', 'P4X', 'P2X', 'P5C']
PEGASUS_REGIONS = ['M4R', 'P3Y', 'M6R']


class Stargate(models.Model):
    _name = 'test_http.stargate'
    _description = 'Stargate'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, store=True, compute='_compute_name', readonly=False)
    address = fields.Char(required=True)
    sgc_designation = fields.Char(store=True, compute='_compute_sgc_designation')
    galaxy_id = fields.Many2one('test_http.galaxy', required=True)
    has_galaxy_crystal = fields.Boolean(store=True, compute='_compute_has_galaxy_crystal', readonly=False)
    glyph_attach = fields.Image(attachment=True)
    glyph_inline = fields.Image(attachment=False)
    glyph_related = fields.Image('Glyph 128', related='glyph_attach', max_width=128, max_height=128, store=True)
    glyph_compute = fields.Image(compute='_compute_glyph_compute')
    galaxy_picture = fields.Image(related='galaxy_id.picture', attachment=True, store=False)
    availability = fields.Float(default=0.99, aggregator="avg")
    last_use_date = fields.Date()

    _sql_constraints = [
        ('address_length', 'CHECK(LENGTH(address) = 6)', "Local addresses have 6 glyphs"),
    ]

    @api.depends('galaxy_id')
    def _compute_has_galaxy_crystal(self):
        milky_way = self.env.ref('test_http.milky_way')
        for gate in self:
            gate.has_galaxy_crystal = gate.galaxy_id == milky_way

    @api.depends('sgc_designation')
    def _compute_name(self):
        for gate in self:
            if not gate.name:
                gate.name = gate.sgc_designation

    @api.depends('address')
    def _compute_sgc_designation(self):
        """ Forge a sgc designation that looks like a real one. """
        for gate in self:
            if gate.galaxy_id.name not in ('Milky Way', 'Pegasus'):
                gate.sgc_designation = False
                continue

            region_part = (
                PEGASUS_REGIONS[gate.id % len(PEGASUS_REGIONS)]
                if gate.galaxy_id.name == 'Pegasus'
                else MILKY_WAY_REGIONS[gate.id % len(MILKY_WAY_REGIONS)]
            )
            local_part = str(int.from_bytes(gate.address.encode(), 'big'))[:3]
            gate.sgc_designation = f'{region_part}-{local_part}'

    @api.depends('glyph_attach')
    def _compute_glyph_compute(self):
        for gate in self:
            gate.glyph_compute = gate.glyph_attach


class Galaxy(models.Model):
    _name = 'test_http.galaxy'
    _description = 'Galaxy'

    name = fields.Char(required=True, help='The galaxy common name.')
    translated_name = fields.Char(translate=True)
    picture = fields.Image(attachment=True, groups="base.group_user")
    stargate_ids = fields.One2many('test_http.stargate', 'galaxy_id', string="stargates")

    @api.model
    def render(self, galaxy_id):
        return self.env['ir.qweb']._render('test_http.tmpl_galaxy', {
            'galaxy': self.browse([galaxy_id])
        })
