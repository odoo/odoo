# Copyright 2022 Acsone SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from openupgradelib import openupgrade, openupgrade_160

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    _logger.info("Migrate translations for field 'product.brand,description'")
    openupgrade_160.migrate_translations_to_jsonb(
        env, [("product.brand", "description")]
    )
