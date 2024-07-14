# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestDocumentsShare(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Folder = cls.env['documents.folder']
        Company = cls.env['res.company']
        Website = cls.env['website']
        cls.website_2 = Website.create({'name': 'Test no company', 'domain': 'https://website_2.com'})
        cls.website_company_1 = Website.create({'name': 'Test company 1', 'domain': 'https://company_1.com'})
        cls.website_company_3 = Website.create({'name': 'Test company 3', 'domain': 'https://company_3.com'})
        cls.website_main_company = cls.env.ref('base.main_company').website_id
        cls.website_main_company.domain = 'https://main.company.com'

        cls.company_1 = Company.create({'name': 'Company 1 with website', 'website_id': cls.website_company_1.id})
        cls.company_3 = Company.create({'name': 'Company 3 with website', 'website_id': cls.website_company_3.id})
        cls.company_without_website = Company.create({'name': 'Company without website'})

        cls.folder_no_company = Folder.create({'name': 'Folder no company'})
        cls.folder_company_1 = Folder.create({'name': 'Folder company 1', 'company_id': cls.company_1.id})
        cls.folder_company_no_website = Folder.create({
            'name': 'Folder company without website',
            'company_id': cls.company_without_website.id
        })

        (cls.document_no_company,
         cls.document_company_1,
         cls.document_company_no_website) = cls.env['documents.document'].create(
            [{
                'datas': b"TEST",
                'name': 'file.txt',
                'mimetype': 'text/plain',
                'folder_id': folder.id,
            } for folder in (cls.folder_no_company, cls.folder_company_1, cls.folder_company_no_website)])
        cls.default_domain = cls.company_without_website.get_base_url()  # Company without website -> default domain

    def _create_documents_share(self, folder, document=None, with_company=None):
        """ Create a documents.share to share a folder or a document (if document parameter is not None). """
        return self.env['documents.share'].with_company(with_company).create({
            'document_ids': [(4, document.id, 0)] if document else False,
            'folder_id': folder.id,
            'name': 'share_link_ids',
            'type': 'ids' if document else 'domain',
        })

    def test_initial_data(self):
        self.assertFalse(self.folder_no_company.company_id)
        self.assertTrue(self.folder_company_1.company_id.website_id)
        self.assertTrue(self.folder_company_no_website.company_id)
        self.assertFalse(self.folder_company_no_website.company_id.website_id)
        # All domains are different and not False
        self.assertEqual(len({domain for domain in (self.folder_company_1.company_id.website_id.domain,
                                                    self.website_main_company.domain,
                                                    self.website_2.domain,
                                                    self.default_domain) if domain}), 4)
        self.assertTrue(self.env.company, self.env.ref('base.main_company'))
        self.assertNotEqual(self.default_domain, 'https://main.company.com')

    def test_share_url_domain(self):
        """ Test the default share domain URL and website in various setup.

        It also tests that the website can be changed manually and that the
        share domain is adjusted accordingly.
        """
        # Test share URL domain when sharing documents/folder without a company.
        documents_share = self._create_documents_share(self.folder_no_company, self.document_no_company)
        self.assertEqual(documents_share.website_id, self.website_main_company)
        self.assertTrue(documents_share.full_url.startswith('https://main.company.com'))
        documents_share = self._create_documents_share(self.folder_no_company, self.document_no_company,
                                                       with_company=self.company_1)
        self.assertTrue(documents_share.full_url.startswith('https://company_1.com'))
        documents_share = self._create_documents_share(self.folder_no_company)
        self.assertTrue(documents_share.full_url.startswith('https://main.company.com'))
        self.assertEqual(documents_share.website_id, self.website_main_company)
        documents_share = self._create_documents_share(self.folder_no_company, with_company=self.company_1)
        self.assertTrue(documents_share.full_url.startswith('https://company_1.com'))
        # Test share URL domain when sharing documents/folder with a company with a website.
        documents_share = self._create_documents_share(self.folder_company_1, self.document_company_1)
        self.assertEqual(documents_share.website_id, self.website_company_1)
        self.assertTrue(documents_share.full_url.startswith('https://company_1.com'))
        documents_share = self._create_documents_share(self.folder_company_1, self.document_company_1, self.company_3)
        self.assertTrue(documents_share.full_url.startswith('https://company_1.com'))
        documents_share = self._create_documents_share(self.folder_company_1)
        self.assertEqual(documents_share.website_id, self.website_company_1)
        self.assertTrue(documents_share.full_url.startswith('https://company_1.com'))
        # Test share URL domain when sharing documents/folder with a company without a website.
        documents_share = self._create_documents_share(self.folder_company_no_website, self.document_company_no_website)
        self.assertEqual(documents_share.website_id, self.website_main_company)
        self.assertTrue(documents_share.full_url.startswith('https://main.company.com'))
        documents_share = self._create_documents_share(self.folder_company_no_website)
        self.assertEqual(documents_share.website_id, self.website_main_company)
        self.assertTrue(documents_share.full_url.startswith('https://main.company.com'))
        documents_share = self._create_documents_share(self.folder_company_no_website,
                                                       with_company=self.company_without_website)
        self.assertTrue(documents_share.full_url.startswith(self.default_domain))
        documents_share = self._create_documents_share(self.folder_company_no_website,
                                                       with_company=self.company_without_website)
        self.assertFalse(documents_share.website_id)
        self.assertTrue(documents_share.full_url.startswith(self.default_domain))
        # Test documents/folder sharing with a company without a website and a main website without domain.
        self.website_main_company.domain = ''
        documents_share = self._create_documents_share(self.folder_company_no_website, self.document_company_no_website)
        self.assertEqual(documents_share.website_id, self.website_main_company)
        self.assertTrue(documents_share.full_url.startswith(self.default_domain))
        documents_share = self._create_documents_share(self.folder_company_no_website)
        self.assertEqual(documents_share.website_id, self.website_main_company)
        self.assertTrue(documents_share.full_url.startswith(self.default_domain))
        documents_share = self._create_documents_share(self.folder_company_no_website, with_company=self.company_3)
        self.assertEqual(documents_share.website_id, self.company_3.website_id)
        self.assertTrue(documents_share.full_url.startswith('https://company_3.com'))
        # Test that the URL is updated when changing the website manually
        documents_share = self._create_documents_share(self.folder_no_company, self.document_no_company)
        documents_share.website_id = self.website_2
        self.assertTrue(documents_share.full_url.startswith('https://website_2.com'))
        documents_share = self._create_documents_share(self.folder_company_1, self.document_company_1)
        documents_share.website_id = self.website_2
        self.assertTrue(documents_share.full_url.startswith('https://website_2.com'))
        documents_share = self._create_documents_share(self.folder_company_no_website, self.document_company_no_website)
        documents_share.website_id = self.website_company_1
        self.assertTrue(documents_share.full_url.startswith('https://company_1.com'))
