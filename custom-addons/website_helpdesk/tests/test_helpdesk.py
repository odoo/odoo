from odoo.tests.common import TransactionCase, Form


class HelpdeskWebsite(TransactionCase):

    def test_adapt_helpdesk_menu(self):
        """
        When we have only 1 team on published on the website,
        the menu name should be "Help".
        When we have more than 1 team published on the website,
        each menu is represented by the team's name
        """
        MENU_LABEL_HELP = "Help"
        TEAM_NAME_1 = "team_name_1"
        TEAM_NAME_2 = "team_name_2"
        # we use a new website to not do our test with the default "Customer Care" team into the test
        website = self.env['website'].create({
            'name': 'My Website Test',
            'domain': '',
            'sequence': 20,
        })

        team_1, team_2 = self.env['helpdesk.team'].create([{
            'name': TEAM_NAME_1,
            'website_id': website.id,
            'use_website_helpdesk_form': True,
            'is_published': True,
        }, {
            'name': TEAM_NAME_2,
            'website_id': website.id,
        }])
        self.assertEqual(team_1.website_menu_id.name, MENU_LABEL_HELP, "The default team website label should be 'Help'")
        with Form(team_2) as team_2_form:
            # this trigger the onchange that should update the menu names
            team_2_form.use_website_helpdesk_form = True
            team_2_form.save()
        self.assertEqual(team_1.website_menu_id.name, TEAM_NAME_1, "The team's website label should be the team's name")
        self.assertEqual(team_2.website_menu_id.name, TEAM_NAME_2, "The team's website label should be the team's name")
        with Form(team_1) as team_1_form:
            # this trigger the onchange that should update the menu names
            team_1_form.use_website_helpdesk_form = False
            team_1_form.save()
        self.assertEqual(team_2.website_menu_id.name, MENU_LABEL_HELP, "The team's website label should be reset to 'Help'")
