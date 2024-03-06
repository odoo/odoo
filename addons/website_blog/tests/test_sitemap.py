# Part of Odoo. See LICENSE file for full copyright and licensing details.

# This test is in website_blog to ensure we have pages in the sitemap.

import odoo.tests
from odoo.addons.website.tools import MockRequest
from odoo.addons.website.controllers.main import Website as WebsiteController


@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteLanguage(odoo.tests.HttpCase):

    def test_sitemap_language(self):
        Website = self.env.ref('website.default_website')
        lang_fr = self.env['res.lang']._activate_lang('fr_FR')
        lang_fr.write({'url_code': 'fr'})
        Website.language_ids = self.env.ref('base.lang_en') + lang_fr
        Website.default_lang_id = self.env.ref('base.lang_en')
        blog = self.env['blog.blog'].create({
            "name": 'Blog',
        })
        # Create a published blog post and set a translation for it
        post = self.env['blog.post'].create({
            'name': "Blog Post ENGLISH",
            'website_published': True,
            'blog_id': blog.id,
        })
        post.with_context(lang='fr_FR').write({
            'name': "Blog Post FRENCH",
        })
        with MockRequest(self.env, url_root='/', website=Website, context={'lang': 'fr_FR'}):
            # Create the attachment.
            WebsiteController().sitemap_xml_index()
            sitemap_attachment = self.env['ir.attachment'].search([('name', '=', "/sitemap-%d.xml" % Website.id)])
            print(str(sitemap_attachment.raw))
            if "xxx" in str(sitemap_attachment.raw):
                pass
            print("done")
