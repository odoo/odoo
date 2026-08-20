from odoo import api, fields, models


class TestOrmMany2manyCrew(models.Model):
    _name = 'test_orm.many2many.crew'
    _description = 'Test ORM Many2many Crew'
    _table = 'test_orm_many2many_crew'

    # this actually represents the union of two relations pirate/ship and
    # prisoner/ship, where some of the many2one fields can be NULL
    pirate_id = fields.Many2one('test_orm.many2many.pirate')
    prisoner_id = fields.Many2one('test_orm.many2many.prisoner')
    ship_id = fields.Many2one('test_orm.many2many.ship')


class TestOrmMany2manyShip(models.Model):
    _name = 'test_orm.many2many.ship'
    _description = 'Test ORM Many2many Ship'

    name = fields.Char('Name')
    pirate_ids = fields.Many2many('test_orm.many2many.pirate', 'test_orm_many2many_crew', 'ship_id', 'pirate_id')
    prisoner_ids = fields.Many2many('test_orm.many2many.prisoner', 'test_orm_many2many_crew', 'ship_id', 'prisoner_id')


class TestOrmMany2manyPirate(models.Model):
    _name = 'test_orm.many2many.pirate'
    _description = 'Test ORM Many2many Pirate'

    name = fields.Char('Name')
    ship_ids = fields.Many2many('test_orm.many2many.ship', 'test_orm_many2many_crew', 'pirate_id', 'ship_id')


class TestOrmMany2manyPrisoner(models.Model):
    _name = 'test_orm.many2many.prisoner'
    _description = 'Test ORM Many2many Prisoner'

    name = fields.Char('Name')
    ship_ids = fields.Many2many('test_orm.many2many.ship', 'test_orm_many2many_crew', 'prisoner_id', 'ship_id')


class TestOrmMany2manyAttachment(models.Model):
    _name = 'test_orm.many2many.attachment'
    _description = 'Test ORM Many2many Attachment'
    _access_domain_heavy = True

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    name = fields.Char(compute='_compute_name', compute_sudo=True, store=True)

    @api.depends('res_model', 'res_id')
    def _compute_name(self):
        for rec in self:
            rec.name = self.env[rec.res_model].browse(rec.res_id).display_name

    # DLE P55: `test_cache_invalidation`
    def modified(self, fnames, *args, **kwargs):
        if not self:
            return None
        comodel = self.env[self.res_model]
        if 'res_id' in fnames and 'attachment_ids' in comodel:
            record = comodel.browse(self.res_id)
            record.invalidate_recordset(['attachment_ids'])
            record.modified(['attachment_ids'])
        return super().modified(fnames, *args, **kwargs)


class TestOrmMany2manyAttachmentHost(models.Model):
    _name = 'test_orm.many2many.attachment_host'
    _description = 'Test ORM Many2many Attachment Host'

    attachment_ids = fields.One2many(
        'test_orm.many2many.attachment', 'res_id', bypass_search_access=True,
        domain=lambda self: [('res_model', '=', self._name)],
    )
    m2m_attachment_ids = fields.Many2many(
        'test_orm.many2many.attachment',
        'test_orm_m2m_attachment_host_rel',
        bypass_search_access=True,
    )

    real_binary = fields.Binary(attachment=True)
    real_attachment_ids = fields.One2many(
        'ir.attachment', 'res_id', bypass_search_access=True,
        domain=lambda self: [('res_model', '=', self._name)],
    )
    real_m2m_attachment_ids = fields.Many2many(
        'ir.attachment',
        'test_orm_m2m_real_attachment_host_rel',
        bypass_search_access=True,
    )
