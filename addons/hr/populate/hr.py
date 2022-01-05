# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models
from odoo.tools import populate

class HrDepartment(models.Model):
    _inherit = 'hr.department'

    _populate_sizes = {'small': 5, 'medium': 30, 'large': 200}

    def _populate_factories(self):
        return [
            ('name', populate.constant('department_{counter}')),
        ]

    def _populate(self, size):
        departments = super()._populate(size)
        self._populate_set_parent_departments(departments, size)
        return departments

    def _populate_set_parent_departments(self, departments, size):
        parent_ids = []
        rand = populate.Random('hr.department+parent_generator')

        for dept in departments:
            if rand.random() > 0.3:
                parent_ids.append(dept.id)

        parent_children = defaultdict(lambda: self.env['hr.department'])
        for dept in departments:
            parent = rand.choice(parent_ids)
            if parent < dept.id:
                parent_children[parent] |= dept

        for parent, children in parent_children.items():
            children.write({'parent_id': parent})

class HrJob(models.Model):
    _inherit = 'hr.job'

    _populate_sizes = {'small': 5, 'medium': 20, 'large': 100}
    _populate_dependencies = ['hr.department']

    def _populate_factories(self):
        department_ids = self.env.registry.populated_models['hr.department']

        return [
            ('name', populate.constant('job_{counter}')),
            ('department_id', populate.randomize(department_ids)),
        ]

class HrWorkLocation(models.Model):
    _inherit = 'hr.work.location'

    _populate_sizes = {'small': 2, 'medium': 5, 'large': 20}

    def _populate_factories(self):
        address_id = self.env.ref('base.main_partner').id

        return [
            ('name', populate.constant('work_location_{counter}')),
            ('address_id', populate.constant(address_id)),
        ]

class HrEmployeeCategory(models.Model):
    _inherit = 'hr.employee.category'

    _populate_sizes = {'small': 10, 'medium': 50, 'large': 200}

    def _populate_factories(self):
        return [
            ('name', populate.constant('tag_{counter}')),
        ]

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    _populate_sizes = {'small': 100, 'medium': 2000, 'large': 20000}
    _populate_dependencies = ['hr.department', 'hr.job', 'hr.work.location', 'hr.employee.category']

    def _populate(self, size):
        employees = super()._populate(size)
        self._populate_set_manager(employees)
        return employees

    def _populate_factories(self):
        company_id = self.env.ref('base.main_company').id
        department_ids = self.env.registry.populated_models['hr.department']
        job_ids = self.env.registry.populated_models['hr.job']
        work_location_ids = self.env.registry.populated_models['hr.work.location']
        tag_ids = self.env.registry.populated_models['hr.employee.category']

        def get_tag_ids(values, counter, random):
            return [
                (6, 0, [
                    random.choice(tag_ids) for i in range(random.randint(0, 6))
                ])
            ]

        return [
            ('active', populate.iterate([True, False], [0.9, 0.1])),
            ('company_id', populate.constant(company_id)),
            ('name', populate.constant("employee_{counter}")),
            ('department_id', populate.randomize(department_ids)),
            ('job_id', populate.randomize(job_ids)),
            ('work_location_id', populate.randomize(work_location_ids)),
            ('category_ids', populate.compute(get_tag_ids)),
        ]

    def _populate_set_manager(self, employees):
        manager_ids = []
        rand = populate.Random('hr.employee+manager_generator')

        for employee in employees:
            if rand.random() >= 0.85: # 15% of employees are managers
                manager_ids.append(employee.id)

        for employee in employees:
            manager = rand.choice(manager_ids)
            if manager != employee.id:
                employee.parent_id = manager
