from odoo import Command
from odoo.tests import common

from odoo.addons.mail.tests.common import mail_new_test_user


def set_salary_allocations(employee, rows):
    """Replace an employee's salary allocations in one write.

    `rows` maps a bank account to the `{"amount", "amount_is_percentage",
    "sequence"}` dict the `salary_distribution` JSON used to carry. An account
    the employee holds and `rows` omits keeps its place at 0%, which is what an
    absent JSON key meant.

    The rows are cleared and recreated rather than updated one by one, because
    `@api.constrains` runs inside `write()`: a per-row update would have the
    percentages total read 60 between setting the first row and the second, and
    the set-wise constraint would refuse a set that is valid once complete.
    """
    values = {account.id: dict(vals) for account, vals in rows.items()}
    commands = [Command.clear()]
    for allocation in employee.salary_allocation_ids:
        account_id = allocation.bank_account_id.id
        commands.append(
            Command.create(
                {
                    "bank_account_id": account_id,
                    "sequence": allocation.sequence,
                    "amount": 0.0,
                    "amount_is_percentage": True,
                    **values.pop(account_id, {}),
                }
            )
        )
    for account_id, vals in values.items():
        commands.append(Command.create({"bank_account_id": account_id, **vals}))
    employee.salary_allocation_ids = commands


class TestHrCommon(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.res_users_hr_officer = mail_new_test_user(
            cls.env,
            email="hro@example.com",
            login="hro",
            groups="base.group_user,hr.group_hr_user,base.group_partner_manager",
            name="HR Officer",
        )

        cls.res_users_hr_manager = mail_new_test_user(
            cls.env,
            email="manager@example.com",
            login="manager",
            groups="base.group_user,hr.group_hr_manager,base.group_partner_manager",
            name="HR Admin",
        )

        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Richard",
                "sex": "male",
                "country_id": cls.env.ref("base.be").id,
            }
        )
