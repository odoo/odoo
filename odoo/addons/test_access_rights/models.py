from odoo import api, fields, models
from odoo.fields import Domain


class Test_Access_RightSome_Obj(models.Model):
    _name = "test_access_right.some_obj"
    _description = "Object For Test Access Right"

    val = fields.Integer()
    categ_id = fields.Many2one(comodel_name="test_access_right.obj_categ")
    parent_id = fields.Many2one(comodel_name="test_access_right.some_obj")
    company_id = fields.Many2one(comodel_name="res.company")
    forbidden = fields.Integer(
        default=5,
        groups="test_access_rights.test_group,base.group_portal",
    )
    forbidden2 = fields.Integer(groups="test_access_rights.test_group")
    forbidden3 = fields.Integer(groups=fields.NO_ACCESS)
    forbidden_searchable = fields.Integer(
        compute="_compute_forbidden_searchable",
        search="_search_forbidden_searchable",
        groups=fields.NO_ACCESS,
    )
    write_gated = fields.Integer(write_groups="test_access_rights.test_group")
    write_gated_never = fields.Integer(write_groups=fields.NO_ACCESS)
    write_gated_on_stored = fields.Integer(
        write_groups=lambda records: (
            not records.ids
            or records.env.user.has_group("test_access_rights.test_group")
        )
    )
    read_and_write_gated = fields.Integer(
        write_groups="base.group_system",
        groups="test_access_rights.test_group",
    )

    @api.depends("val")
    def _compute_forbidden_searchable(self):
        for record in self:
            record.forbidden_searchable = record.val

    def _search_forbidden_searchable(self, operator, value):
        return [("val", operator, value)]


class Test_Access_RightContainer(models.Model):
    _name = "test_access_right.container"
    _description = "Test Access Right Container"

    some_ids = fields.Many2many(
        comodel_name="test_access_right.some_obj",
        relation="test_access_right_rel",
        column1="container_id",
        column2="some_id",
    )


class Test_Access_RightInherits(models.Model):
    _name = "test_access_right.inherits"
    _description = "Object for testing related access rights"

    _inherits = {"test_access_right.some_obj": "some_id"}

    some_id = fields.Many2one(
        comodel_name="test_access_right.some_obj",
        required=True,
        ondelete="restrict",
    )


class Test_Access_RightInheritsComputed(models.Model):
    _name = "test_access_right.inherits_computed"
    _description = "Object delegating through a computed, searchable link"

    _inherits = {"test_access_right.some_obj": "some_id"}

    held_id = fields.Many2one(
        comodel_name="test_access_right.some_obj",
        ondelete="restrict",
    )
    some_id = fields.Many2one(
        comodel_name="test_access_right.some_obj",
        compute="_compute_some_id",
        search="_search_some_id",
        compute_sudo=True,
        store=False,
        required=True,
        ondelete="cascade",
    )

    @api.depends("held_id")
    def _compute_some_id(self):
        for record in self:
            record.some_id = record.held_id

    def _search_some_id(self, operator, value):
        return Domain("held_id", operator, value)

    def _create_parent_records(self, data_list):
        for data in data_list:
            data["stored"]["some_id"] = data["stored"].get("held_id")
        super()._create_parent_records(data_list)
        for data in data_list:
            data["stored"]["held_id"] = data["stored"].pop("some_id")


class Test_Access_RightChild(models.Model):
    _name = "test_access_right.child"
    _description = "Object for testing company ir rule"

    parent_id = fields.Many2one(comodel_name="test_access_right.some_obj")


class Test_Access_RightObj_Categ(models.Model):
    _name = "test_access_right.obj_categ"
    _description = "Context dependent searchable model"

    name = fields.Char(required=True)

    @api.model
    def search_fetch(self, domain, field_names=None, offset=0, limit=None, order=None):
        if self.env.context.get("only_media"):
            domain = Domain(domain) & Domain("name", "=", "Media")
        return super().search_fetch(domain, field_names, offset, limit, order)


class Test_Access_RightTicket(models.Model):
    _name = "test_access_right.ticket"
    _description = "Fake ticket For Test Access Right"

    name = fields.Char()
    message_partner_ids = fields.Many2many(comodel_name="res.partner")


class ResPartner(models.Model):
    _inherit = "res.partner"

    # named for this module: account declares res.partner.currency_id and its
    # _compute_currency_id too, and the two would merge into one field
    test_access_currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_test_access_currency_id",
        readonly=True,
    )
    test_access_monetary = fields.Monetary(currency_field="test_access_currency_id")

    @api.depends("company_id.currency_id")
    def _compute_test_access_currency_id(self):
        for partner in self:
            partner.test_access_currency_id = partner.sudo().company_id.currency_id
