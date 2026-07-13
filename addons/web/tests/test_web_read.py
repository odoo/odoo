from odoo import Command
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged('post_install', '-at_install')
class TestWebReadX2manyAccessRules(TransactionCase):
    """ x2many cache pollution in web_read."""

    def test_web_read_filters_inaccessible_x2many_records(self):
        # web_read must filter inaccessible x2many records when the ORM cache
        # contains unaccessible ids.
        #
        # Context:
        # - There are two companies:
        #       Company A (allowed) and Company B (blocked).
        # - There are one user:
        #       user_with_restricted_access who has access only to company A.
        # - There are two partners:
        #       partner_accessible in company A and partner_blocked in company B.
        # - There are a partner category:
        #       links the two partners via a x2many field (partner_ids).
        # Steps:
        # - We use web_read twice on the partner category with the restricted user.
        # - The first web_read call populates the x2many cache with only partner_accessible id.
        # - We invalidate the x2many cache and repopulate it with a sudo fetch. Now cache contains both partner_accessible and partner_blocked ids.
        # - The second web_read call must not return the blocked partner, even if its id is in the cache.
        #
        # Expected:
        # - web_read must read only accessible partners.
        company_allowed = self.env['res.company'].create({'name': 'Company A'})
        company_blocked = self.env['res.company'].create({'name': 'Company B'})

        user_with_restricted_access = new_test_user(
            self.env,
            login='restricted@test.com',
            groups='base.group_user,base.group_partner_manager',
            name='User with Restricted Access',
            company_id=company_allowed.id,
            company_ids=[Command.set([company_allowed.id])],
        )

        # We create one internal user and one portal user to get two partner records
        # Behaviors:
        # - internal user's partner is readable by the restricted user,
        # - portal user's partner has partner_share=True and is blocked by record rules
        #   when it belongs to another company.

        partner_accessible = self.env['res.partner'].create({
            'name': 'Accessible Partner',
            'company_id': company_allowed.id,
        })

        portal_user = new_test_user(
            self.env,
            login='blocked@test.com',
            groups='base.group_portal',
            name='Blocked Partner',
            company_id=company_blocked.id,
        )
        partner_blocked = portal_user.partner_id
        partner_blocked.company_id = company_blocked.id

        category = self.env['res.partner.category'].create({
            'name': 'Odoo Lovers',
            'partner_ids': [Command.set([
                partner_accessible.id,
                partner_blocked.id,
            ])],
        })

        web_specification = {
            'id': {},
            'name': {},
            'partner_ids': {'fields': {'display_name': {}}},
        }

        # Start with a clean cache.
        self.env.invalidate_all()

        # Use the restricted user.
        record = category.with_user(user_with_restricted_access).with_context(
            allowed_company_ids=[company_allowed.id], active_test=False
        )

        # First web_read must only return accessible partner.
        result = record.web_read(web_specification)
        ids_returned = [p['id'] for p in result[0]['partner_ids']]
        self.assertIn(partner_accessible.id, ids_returned)
        self.assertNotIn(
            partner_blocked.id, ids_returned,
            "First web_read must not expose the blocked partner.",
        )

        # Simulate pollution cache: remove cache from previous web_read, then repopulate with sudo.
        category.invalidate_recordset(['partner_ids'], flush=False)
        category.sudo().fetch(['partner_ids'])

        # Second web_read must always return only accessible partner.
        result = record.web_read(web_specification)
        ids_returned = [p['id'] for p in result[0]['partner_ids']]
        self.assertIn(partner_accessible.id, ids_returned)
        self.assertNotIn(
            partner_blocked.id, ids_returned,
            "Second web_read must not expose inaccessible x2many records.",
        )
