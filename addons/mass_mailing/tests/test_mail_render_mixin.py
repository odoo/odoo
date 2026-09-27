from odoo.addons.mass_mailing.tests.common import MassMailCommon


class TestMailRenderMixin(MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_mailing_list()

    def test_shorten_links(self):
        # Prepare
        mailing = self.env['mailing.mailing'].create({
            'subject': 'TestShortener',
            'body_html': """<!DOCTYPE html>
            <html>
                <head>
                    <link type="text/css" rel="stylesheet" href="http://test.external.link/style1.css"/>
                    <meta/>
                    <script type="text/javascript" src="http://test.external.link/javascript1.js"></script>
                </head>
                <body>
                    <img src="http://test.external.link/img.png" loading="lazy"/>
                    <a id="url0" href="https://test.external.link/link">x</a>
                    <div><a id="url1" href="https://test.cdn/web/content/local_link" data-no-tracking>x</a></div>
                    <span style="background-image: url(&#39;http://test.cdn/web/image/2&#39;)">xxx</span>
                    <div widget="html"><span class="toto">
                            span<span class="fa"></span><img src="http://test.cdn/web/image/1" loading="lazy">
                        </span></div>
                </body>
            </html>""",
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'reply_to_mode': 'new',
            'reply_to': self.email_reply_to,
            'contact_list_ids': [(6, 0, self.mailing_list_1.ids)],
            'keep_archives': True,
        })

        # Execute
        with self.mock_mail_gateway():
            mailing.action_send_mail()

        # Assert
        for contact in self.mailing_list_1.contact_ids:
            new_mail = self._find_mail_mail_wrecord(contact)
            for link_info in [('url0', 'https://test.external.link/link', True),
                              ('url1', 'https://test.cdn/web/content/local_link', False)]:
                link_params = {
                    'utm_medium': 'Email',
                    'utm_source': 'Mass Mailing',
                    'utm_reference': f'mailing.mailing,{mailing.id}',
                }
                self.assertLinkShortenedHtml(
                    new_mail.mail_message_id.body,
                    link_info,
                    link_params=link_params,
                )
