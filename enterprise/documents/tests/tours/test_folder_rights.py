# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import HttpCase
from odoo import Command


@tagged("post_install", "-at_install")
class TestDocumentFolderRights(HttpCase):
    def test_document_folder_rights_for_multi_company_tour(self):
        company_a = self.env['res.company'].create({'name': 'Company_A'})
        self.env.ref('base.user_admin').company_ids = [Command.link(company_a.id)]
        self.env['documents.document'].create({
            "access_internal": "view",
            "company_id": self.env.company.id,
            "owner_id": self.env.ref('base.user_root').id,
            "name": "Folder1",
            "type": "folder",
        })

        self.start_tour("/odoo", 'test_document_folder_rights_for_multi_company', login='admin')
