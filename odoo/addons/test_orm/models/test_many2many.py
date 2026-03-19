from odoo import api, fields, models


class TestMany2manyCrew(models.Model):
    _name = 'test_many2many.crew'
    _description = 'All yaaaaaarrrrr by ship'
    _table = 'test_many2many_crew'

    # this actually represents the union of two relations pirate/ship and
    # prisoner/ship, where some of the many2one fields can be NULL
    pirate_id = fields.Many2one('test_many2many.pirate')
    prisoner_id = fields.Many2one('test_many2many.prisoner')
    ship_id = fields.Many2one('test_many2many.ship')


class TestMany2manyShip(models.Model):
    _name = 'test_many2many.ship'
    _description = 'Yaaaarrr machine'

    name = fields.Char('Name')
    pirate_ids = fields.Many2many('test_many2many.pirate', 'test_many2many_crew', 'ship_id', 'pirate_id')
    prisoner_ids = fields.Many2many('test_many2many.prisoner', 'test_many2many_crew', 'ship_id', 'prisoner_id')


class TestMany2manyPirate(models.Model):
    _name = 'test_many2many.pirate'
    _description = 'Yaaarrr'

    name = fields.Char('Name')
    ship_ids = fields.Many2many('test_many2many.ship', 'test_many2many_crew', 'pirate_id', 'ship_id')


class TestMany2manyPrisoner(models.Model):
    _name = 'test_many2many.prisoner'
    _description = 'Yaaarrr minions'

    name = fields.Char('Name')
    ship_ids = fields.Many2many('test_many2many.ship', 'test_many2many_crew', 'prisoner_id', 'ship_id')


class TestMany2manyAttachment(models.Model):
    _name = 'test_many2many.attachment'
    _description = 'Attachment'
    _access_domain_heavy = True

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    name = fields.Char(compute='_compute_name', compute_sudo=True, store=True)

    @api.depends('res_model', 'res_id')
    def _compute_name(self):
        for rec in self:
            rec.name = self.env[rec.res_model].browse(rec.res_id).display_name


class TestMany2manyAttachmentHost(models.Model):
    _name = 'test_many2many.attachment.host'
    _description = 'Attachment Host'

    m2m_attachment_ids = fields.Many2many(
        'test_many2many.attachment', bypass_search_access=True,
    )

    real_binary = fields.Binary(attachment=True)
    real_m2m_attachment_ids = fields.Many2many(
        'ir.attachment', bypass_search_access=True,
    )