from odoo import models, fields, api

class DemoTag(models.Model):
    _name = 'demo.tag'
    _description = 'Demo Tags'

    name = fields.Char(string='Tag Name', index=True, required=True)
    active = fields.Boolean(default=True, help="Set active.")

class DemoExpenseTutorial(models.Model):
    _name = 'demo.expense.tutorial'
    _description = 'Demo Expense Tutorial'

    name = fields.Char('Description', required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)

    # https://www.odoo.com/documentation/12.0/reference/orm.html#odoo.fields.Many2many
    # Many2many(comodel_name=<object object>, relation=<object object>, column1=<object object>, column2=<object object>, string=<object object>, **kwargs)
    #
    # relation: database table name
    #

    # By default, the relationship table name is the two table names
    # joined with an underscore and _rel appended at the end.
    # In the case of our books or authors relationship, it should be named demo_expense_tutorial_demo_tag_rel.

    tag_ids = fields.Many2many('demo.tag', 'demo_expense_tag', 'demo_expense_id', 'tag_id', string='Tges')
    sheet_id = fields.Many2one('demo.expense.sheet.tutorial', string="Expense Report")

    # Related (Reference) fields (不會存在 db)
    # readonly default 為 True
    # store default 為 False
    gender = fields.Selection(string='Gender', related='employee_id.gender')

    def button_sheet_id(self):
        return {
            'view_mode': 'form',
            'res_model': 'demo.expense.sheet.tutorial',
            'res_id': self.sheet_id.id,
            'type': 'ir.actions.act_window'
        }


class DemoExpenseSheetTutorial(models.Model):
    _name = 'demo.expense.sheet.tutorial'
    _description = 'Demo Expense Sheet Tutorial'

    name = fields.Char('Expense Demo Report Summary', required=True)

    # One2many is a virtual relationship, there must be a Many2one field in the other_model,
    # and its name must be related_field
    expense_line_ids = fields.One2many(
        'demo.expense.tutorial', # related model
        'sheet_id', # field for "this" on related model
        string='Expense Lines')

    def add_demo_expense_record(self):
        # (0, _ , {'field': value}) creates a new record and links it to this one.

        data_1 = self.env.ref('demo_expense_tutorial_v1.demo_expense_tutorial_data_1')

        tag_data_1 = self.env.ref('demo_expense_tutorial_v1.demo_tag_data_1')
        tag_data_2 = self.env.ref('demo_expense_tutorial_v1.demo_tag_data_2')

        for record in self:
            # creates a new record
            val = {
                'name': 'test_data',
                'employee_id': data_1.employee_id.id,
                'tag_ids': [(6, 0, [tag_data_1.id, tag_data_2.id])]
            }

            self.expense_line_ids = [(0, 0, val)]

    def link_demo_expense_record(self):
        # (4, id, _) links an already existing record.

        data_1 = self.env.ref('demo_expense_tutorial_v1.demo_expense_tutorial_data_1')

        for record in self:
            # link already existing record
            self.expense_line_ids = [(4, data_1.id, 0)]

    def replace_demo_expense_record(self):
        # (6, _, [ids]) replaces the list of linked records with the provided list.

        data_1 = self.env.ref('demo_expense_tutorial_v1.demo_expense_tutorial_data_1')
        data_2 = self.env.ref('demo_expense_tutorial_v1.demo_expense_tutorial_data_2')

        for record in self:
            # replace multi record
            self.expense_line_ids = [(6, 0, [data_1.id, data_2.id])]

    def button_line_ids(self):
        return {
            'name': 'Demo Expense Line IDs',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'demo.expense.tutorial',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('sheet_id', '=', self.id)],
        }

    def name_get(self):
        names = []
        for record in self:
            name = '%s-%s' % (record.create_date.date(), record.name)
            names.append((record.id, name))
        return names

    # odoo14/odoo/odoo/addons/base/models/ir_model.py
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args + ['|', ('id', operator, name), ('name', operator, name)]
        # domain = args + [ ('name', operator, name)]
        # domain = args + [ ('id', operator, name)]
        return self._search(domain, limit=limit)
