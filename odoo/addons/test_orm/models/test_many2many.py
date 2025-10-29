from odoo import api, fields, models


class Test_Many2many_Attachment(models.Model):
    _name = 'test_many2many.attachment'
    _description = 'Attachment'

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    name = fields.Char(compute='_compute_name', compute_sudo=True, store=True)

    @api.depends('res_model', 'res_id')
    def _compute_name(self):
        for rec in self:
            rec.name = self.env[rec.res_model].browse(rec.res_id).display_name

    # override those methods for many2many search
    def _search(self, domain, offset=0, limit=None, order=None, *, active_test=True, bypass_access=False):
        return super()._search(domain, offset, limit, order, active_test=active_test, bypass_access=bypass_access)

    def _check_access(self, operation):
        return super()._check_access(operation)

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


class Test_Many2many_AttachmentHost(models.Model):
    _name = 'test_many2many.attachment.host'
    _description = 'Attachment Host'

    attachment_ids = fields.One2many(
        'test_many2many.attachment', 'res_id', bypass_search_access=True,
        domain=lambda self: [('res_model', '=', self._name)],
    )
    m2m_attachment_ids = fields.Many2many(
        'test_many2many.attachment', bypass_search_access=True,
    )


class Test_Many2many_Crew(models.Model):
    _name = 'test_many2many.crew'
    _description = 'All yaaaaaarrrrr by ship'
    _table = 'test_many2many_crew'

    # this actually represents the union of two relations pirate/ship and
    # prisoner/ship, where some of the many2one fields can be NULL
    pirate_id = fields.Many2one('test_many2many.pirate')
    prisoner_id = fields.Many2one('test_many2many.prisoner')
    ship_id = fields.Many2one('test_many2many.ship')


class Test_Many2many_Ship(models.Model):
    _name = 'test_many2many.ship'
    _description = 'Yaaaarrr machine'

    name = fields.Char('Name')
    pirate_ids = fields.Many2many('test_many2many.pirate', 'test_many2many_crew', 'ship_id', 'pirate_id')
    prisoner_ids = fields.Many2many('test_many2many.prisoner', 'test_many2many_crew', 'ship_id', 'prisoner_id')


class Test_Many2many_Pirate(models.Model):
    _name = 'test_many2many.pirate'
    _description = 'Yaaarrr'

    name = fields.Char('Name')
    ship_ids = fields.Many2many('test_many2many.ship', 'test_many2many_crew', 'pirate_id', 'ship_id')


class Test_Many2many_Prisoner(models.Model):
    _name = 'test_many2many.prisoner'
    _description = 'Yaaarrr minions'

    name = fields.Char('Name')
    ship_ids = fields.Many2many('test_many2many.ship', 'test_many2many_crew', 'prisoner_id', 'ship_id')
