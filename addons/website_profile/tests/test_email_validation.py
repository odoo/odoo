# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestEmailValidationBannerFix(HttpCase):

    def test_congratulations_banner_disappears_after_validation(self):
        """Test that congratulations banner doesn't persist across page loads"""

        user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test@example.com',
            'email': 'test@example.com',
            'password': 'testpassword',
            'karma': 0,
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })

        self.env['slide.channel'].create({
            'name': 'Test Course',
            'website_published': True,
            'enroll': 'public',
            'visibility': 'public',
        })

        self.authenticate(user.login, 'testpassword')

        response = self.url_open('/slides')
        response_text = response.content.decode()
        self.assertTrue(
            'not yet been verified' in response_text.lower(),
            "Unvalidated users should still see verification banner"
        )

        user.write({'karma': 3})
        session = self.session
        session['validation_email_done'] = True

        self.url_open('/slides')
        response2 = self.url_open('/slides')
        response_text2 = response2.content.decode()
        self.assertNotIn('Congratulations', response_text2.lower(),
                        "Congratulations banner should NOT reappear on refresh")

        response3 = self.url_open('/slides')
        response_text3 = response3.content.decode()
        self.assertNotIn('Congratulations', response_text3.lower(),
                        "Banner should stay hidden on subsequent visits")
