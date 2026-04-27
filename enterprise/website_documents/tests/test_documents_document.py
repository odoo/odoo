# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class TestDocumentsShare(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Document = cls.env['documents.document']
        Company = cls.env['res.company']
        Website = cls.env['website']
        cls.company_1 = Company.create({'name': 'Company 1 with website'})
        cls.company_2 = Company.create({'name': 'Company 2 with website'})
        cls.company_3 = Company.create({'name': 'Company 3 with website'})
        cls.company_without_website = Company.create({'name': 'Company without website'})

        cls.website_company_1 = Website.create({
            'name': 'Test company 1', 'domain': 'https://company_1.com', 'company_id': cls.company_1.id})
        cls.website_company_2 = Website.create({
            'name': 'Test company 2', 'domain': 'https://website_2.com', 'company_id': cls.company_2.id})
        cls.website_company_3 = Website.create({
            'name': 'Test company 3', 'domain': 'https://company_3.com', 'company_id': cls.company_3.id})
        cls.website_main_company = cls.env.ref('base.main_company').website_id
        cls.website_main_company.domain = 'https://main.company.com'

        cls.folder = Document.create({'name': 'Folder no company', 'type': 'folder'})

        cls.default_domain = cls.company_without_website.get_base_url()  # Company without website -> default domain

        cls.user = cls.env['res.users'].create({
            'name': 'User 1',
            'login': 'user_1',
            'company_id': cls.company_1.id,
            'company_ids': [Command.set((cls.company_1 + cls.company_2).ids)],
        })

    def test_share_url_domain(self):
        """ Test the default document access_url domain and website in various setup.

        It also tests that the website can be changed manually and that the
        access_url domain is adjusted accordingly.
        """
        # Test URL domain when sharing documents without a company.
        self.assertEqual(self.folder.website_id, self.website_main_company)
        self.assertSequenceEqual(self.folder.access_url[:24], 'https://main.company.com')

        # Test URL domain when sharing documents with a company with a website.
        self.folder.company_id = self.company_1
        self.assertSequenceEqual(self.folder.access_url[:21], 'https://company_1.com')

        # Test share URL domain when sharing documents/folder with a company without a website.
        self.folder.company_id = self.company_without_website
        self.assertEqual(self.folder.website_id, self.website_main_company)
        self.assertTrue(self.folder.access_url.startswith('https://main.company.com'))

        # Test documents/folder sharing with a company without a website and a main website without domain.
        self.website_main_company.domain = ''
        self.folder.company_id = self.company_without_website
        self.assertEqual(self.folder.website_id, self.website_main_company)
        self.assertTrue(self.folder.access_url.startswith(self.default_domain))

        # Test that the URL is updated when changing the website manually
        self.folder.website_id = self.website_company_2
        self.assertTrue(self.folder.access_url.startswith('https://website_2.com'))

    def test_documents_website_id(self):
        self.assertEqual(self.website_company_1.company_id, self.company_1)
        self.assertEqual(self.website_company_2.company_id, self.company_2)
        self.assertEqual(self.website_company_3.company_id, self.company_3)

        # test on create
        with self.assertRaises(AccessError):
            self.env['documents.document'].with_user(self.user).create({
                'name': 'test1.txt',
                'company_id': self.company_1.id,
                'website_id': self.website_company_3.id,
            })
        with self.assertRaises(AccessError):
            self.env['documents.document'].with_user(self.user).create({
                'name': 'test2.txt',
                'website_id': self.website_company_3.id,
            })
        # don't raise AccessError in sudo mode
        self.env['documents.document'].with_user(self.user).sudo().create({
            'name': 'test2.txt',
            'website_id': self.website_company_3.id,
        })
        self.document_1 = self.env['documents.document'].with_user(self.user).create({
            'name': 'doc1.txt',
            'company_id': self.company_1.id,
            'website_id': self.website_company_2.id,
        })
        self.document_2 = self.env['documents.document'].create({
            'name': 'doc2.txt',
            'company_id': self.company_3.id,
        })
        self.document_without_company = self.env['documents.document'].with_user(self.user).create({
            'website_id': self.website_company_1.id,
        })
        self.document_without_website = self.env['documents.document'].with_user(self.user).create({
            'company_id': self.company_1.id,
            'website_id': False,
        })
        self.assertFalse(self.document_without_website.website_id)

        # test on write
        with self.assertRaises(AccessError):
            (self.document_1 + self.document_2).website_id = self.website_company_3.id
        self.document_2.website_id = self.website_company_3.id
        (self.document_2 + self.document_without_company).website_id = self.website_company_2.id
