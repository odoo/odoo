# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import tagged, TransactionCase

_logger = logging.getLogger(__name__)

@tagged('post_install', '-at_install')
class TestThemeScope(TransactionCase):

    def test_scope(self):
        websites_themes = self.env['website'].get_test_themes_websites()
        assets_count = 0
        attachments_count = 0
        fails = []
        for website in websites_themes:
            prefix = f'{website.theme_id.name}/'
            slash_prefix = f'/{website.theme_id.name}/'
            theme_module = self.env['ir.module.module'].search([
                ('name', '=', website.theme_id.name),
            ])
            assets = theme_module._get_module_data('ir.asset')
            for asset in assets:
                if not asset.path.startswith(prefix) and not asset.path.startswith(slash_prefix):
                    fails.append(f"Asset {asset.id} {asset.key} references outside of theme {website.theme_id.name}: {asset.path}")
            assets_count += len(assets)
            attachments = theme_module._get_module_data('ir.attachment')
            for attachment in attachments:
                if not attachment.url.startswith(slash_prefix):
                    fails.append(f"Attachment {attachment.id} {attachment.key} references outside of theme {website.theme_id.name}: {attachment.url}")
            attachments_count += len(attachments)
        _logger.info(f"Verified {assets_count} assets and {attachments_count} attachments")
        self.assertFalse(fails, "\n".join(fails))
