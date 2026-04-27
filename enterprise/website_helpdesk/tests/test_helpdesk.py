import re

from odoo.tests.common import HttpCase, TransactionCase
from lxml import html


class TestHelpdesk(HttpCase):
    def setUp(self):
        super().setUp()
        self.team_without_web_form = self.env['helpdesk.team'].create({
            'name': 'Team without Web Form',
            'is_published': True,
        })

    def test_create_ticket_portal(self):
        # Only one team has enabled the website form then Help website menu should open the Ticket Submit page
        # If that team has enabled Knowledge then it should open Knowledge page
        team = self.env['helpdesk.team'].search([('use_website_helpdesk_form', '=', True)], limit=1)
        self.env['helpdesk.team'].search([('id', '!=', team.id)]).use_website_helpdesk_form = False
        response = self.url_open('/helpdesk')
        self.assertEqual(response.status_code, 200)
        expected_string = "How can we help you?" if team.use_website_helpdesk_knowledge else "Submit a Ticket"
        search_result = re.search(expected_string.encode(), response.content).group().decode()
        self.assertEqual(search_result, expected_string)

        # multiple teams have enabled the website form then Help website menu should refere to the Team selection page
        self.team_without_web_form.use_website_helpdesk_form = True
        other_response = self.url_open('/helpdesk')
        self.assertEqual(response.status_code, 200)
        expected_string = "Select your Team for help"
        search_result = re.search(expected_string.encode(), other_response.content).group().decode()
        self.assertEqual(search_result, expected_string)

    def test_helpdesk_team_visibility(self):
        test_website = self.env['website'].create({'name': 'test website', 'sequence': 5})
        new_teams = [('Test team1', self.env.ref('website.default_website')),
                    ('Test team2', test_website),
                    ('Test team3', test_website)]
        for name, website in new_teams:
            self.env['helpdesk.team'].create([{
                'name': name,
                'use_website_helpdesk_form': True,
                'website_id': website.id,
                'is_published': True,
            }])
        response = self.url_open('/helpdesk')
        tree = html.fromstring(response.content)
        team_names = tree.xpath('//article[contains(@class, "team_card")]')

        self.assertEqual(len(team_names), 2, "Expected exactly 2 helpdesk teams to be rendered")


class TestHelpdeskMenu(TransactionCase):
    def test_menu_item_visibility(self):
        website = self.env['website'].create({
            'name': 'test website'
        })
        public_user = self.env.ref('base.public_user')
        non_helpdesk_menu = self.env['website.menu'].create({
            'name': 'Menu with helpdesk in URL',
            'url': '/helpdesk-123',
            'website_id': website.id,
        })
        team = self.env['helpdesk.team'].create({
            'name': 'Test team',
            'use_website_helpdesk_form': True,
            'website_id': website.id,
        })

        non_helpdesk_menu.invalidate_recordset(["is_visible"])
        self.assertTrue(non_helpdesk_menu.with_user(public_user).is_visible, "Item with helpdesk in URL should stay visible.")
        self.assertTrue(team.website_menu_id.is_visible)
        team.use_website_helpdesk_form = False
        self.assertFalse(team.website_menu_id.is_visible)

    def test_archive_multiple_teams_different_websites(self):
        """ Test archiving multiple helpdesk teams linked to different websites. """
        websites = self.env['website'].create([{'name': 'W1'}, {'name': 'W2'}])

        teams = self.env['helpdesk.team'].create([{
            'name': f'Team of {website.name}',
            'use_website_helpdesk_form': True,
            'website_id': website.id,
        } for website in websites
        ])

        teams.write({'active': False})
        self.assertFalse(any(t.active for t in teams), "Both teams should be archived without errors.")

        # Verify that a website menu was created for each team and is linked to the correct website
        for i, team in enumerate(teams):
            self.assertTrue(team.website_menu_id and team.website_menu_id.exists(), f"Expected a website menu to be created for {team.name}")
            self.assertEqual(team.website_menu_id.website_id, websites[i])
        self.assertNotEqual(teams[0].website_menu_id.id, teams[1].website_menu_id.id, "Each team should have its own distinct menu")
