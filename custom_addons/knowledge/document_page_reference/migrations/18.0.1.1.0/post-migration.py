# Copyright 2025 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    for item in env["document.page"].search([("content", "ilike", "${")]):
        item.content = re.sub(r"\${(.+)}", r"{{\1}}", item.content)
