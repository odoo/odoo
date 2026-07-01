# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    """Set the value of the analytic_domain field."""
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE mis_report_instance_period
        SET analytic_domain = CONCAT('[("analytic_distribution_search", "in", [', analytic_account_id::VARCHAR, '])]')
        WHERE analytic_account_id IS NOT NULL
        """,  # noqa: E501
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE mis_report_instance
        SET analytic_domain = CONCAT('[("analytic_distribution_search", "in", [', analytic_account_id::VARCHAR, '])]')
        WHERE analytic_account_id IS NOT NULL
        """,  # noqa: E501
    )
