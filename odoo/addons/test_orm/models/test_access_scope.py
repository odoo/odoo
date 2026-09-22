from odoo import fields, models


class TestOrmScopeTag(models.Model):
    _name = "test_orm.scope_tag"
    _description = "Tag whose flag a record rule reads through a path"

    name = fields.Char()
    visible = fields.Boolean()


class TestOrmScopeBox(models.Model):
    _name = "test_orm.scope_box"
    _description = "Box holding the x2many fields a user reads"

    name = fields.Char()
    item_ids = fields.One2many(
        comodel_name="test_orm.scope_item",
        inverse_name="box_id",
    )
    gated_ids = fields.One2many(
        comodel_name="test_orm.scope_gated",
        inverse_name="box_id",
    )
    narrow_ids = fields.One2many(
        comodel_name="test_orm.scope_narrow",
        inverse_name="box_id",
    )


class TestOrmScopeItem(models.Model):
    _name = "test_orm.scope_item"
    _description = "Item a rule admits when its tag is visible"

    name = fields.Char()
    box_id = fields.Many2one(comodel_name="test_orm.scope_box")
    tag_id = fields.Many2one(comodel_name="test_orm.scope_tag")


class TestOrmScopeBlock(models.Model):
    _name = "test_orm.scope_block"
    _description = "Row that hides a gated record from every user's search"

    gated_id = fields.Many2one(comodel_name="test_orm.scope_gated")


class TestOrmScopeGated(models.Model):
    _name = "test_orm.scope_gated"
    _description = "Record whose _search reads another model"
    # declared narrower than what the override reads: the searches it runs
    # are what the cache must follow
    _search_visibility_fields = ()

    name = fields.Char()
    box_id = fields.Many2one(comodel_name="test_orm.scope_box")

    def _search(self, domain, *args, bypass_access=False, **kwargs):
        if not (self.env.su or bypass_access):
            blocks = self.env["test_orm.scope_block"].sudo().search([])
            domain = [*domain, ("id", "not in", blocks.gated_id.ids)]
        return super()._search(domain, *args, bypass_access=bypass_access, **kwargs)


class TestOrmScopeNarrow(models.Model):
    _name = "test_orm.scope_narrow"
    _description = "Record whose _search reads a field it does not declare"
    _search_visibility_fields = ()

    name = fields.Char()
    box_id = fields.Many2one(comodel_name="test_orm.scope_box")
    hidden = fields.Boolean()

    def _search(self, domain, *args, bypass_access=False, **kwargs):
        if not (self.env.su or bypass_access):
            domain = [*domain, ("hidden", "=", False)]
        return super()._search(domain, *args, bypass_access=bypass_access, **kwargs)
