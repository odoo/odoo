from odoo import api, fields, models


class TestOrmAcl(models.Model):
    _name = 'test_orm.acl'
    _description = 'Test ORM ACL'

    name = fields.Char()
    many2one_id = fields.Many2one('test_orm.acl.relations')


class TestOrmAclRelations(models.Model):
    _name = 'test_orm.acl.relations'
    _description = 'Test ORM ACL Relations'

    name = fields.Char()


class TestOrmAclPartner(models.Model):
    _name = 'test_orm.acl.partner'
    _description = 'Test ORM ACL Partner'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    bank_ids = fields.One2many('test_orm.acl.partner.bank', 'partner_id')


class TestOrmAclPartnerBank(models.Model):
    _name = 'test_orm.acl.partner.bank'
    _rec_name = 'account_number'
    _description = 'Test ORM ACL Partner Bank'

    account_number = fields.Char()
    holder_name = fields.Char(compute='_compute_account_holder_name', readonly=False, store=True)
    partner_id = fields.Many2one(comodel_name='test_orm.acl.partner', domain=['|', ('is_company', '=', True), ('parent_id', '=', False)], required=True)

    @api.depends('partner_id')
    def _compute_account_holder_name(self):
        for account in self:
            if not account.holder_name:
                account.holder_name = account.partner_id.name
