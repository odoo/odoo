import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Company = env["res.company"].sudo().with_context(active_test=False)
    Category = env["pendapatan.category"].sudo().with_context(active_test=False)
    parent = env.ref("base.main_company")
    branches = Company.search([
        ("id", "child_of", parent.id),
        ("id", "!=", parent.id),
    ])
    source_categories = Category.search([("company_id", "=", parent.id)])
    copied = 0

    for branch in branches:
        for category in source_categories:
            existing = Category.search([
                ("company_id", "=", branch.id),
                ("code", "=", category.code),
            ], limit=1)
            if existing:
                continue
            category.copy({"company_id": branch.id})
            copied += 1

    income_journals = env["pendapatan.pendapatan"].sudo().search([
        ("journal_id", "!=", False),
        ("department_id", "!=", False),
    ])
    for income in income_journals:
        journal_values = {
            "company_id": income.company_id.id,
            "department_id": income.department_id.id,
            "unit_name": income.department_id.name,
        }
        if "unit_dept" in income.journal_id._fields:
            journal_values["unit_dept"] = income.department_id.sif_journal_unit_dept
        income.journal_id.write(journal_values)

    _logger.info(
        "Copied %s parent-company income categories to %s branches and synchronized %s linked income journals.",
        copied,
        len(branches),
        len(income_journals),
    )
