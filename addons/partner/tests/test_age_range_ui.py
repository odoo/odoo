from lxml import etree

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPartnerAgeRangeUi(TransactionCase):
    """The age range model has to be reachable, not merely present.

    ``partner`` grants ``base.group_partner_manager`` create/write/unlink on
    ``res.partner.age.range``. Until these views existed the model had no
    action and no menu anywhere in the workspace, so that right could not be
    exercised and the cohorts could only be seeded from a data file.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AgeRange = cls.env["res.partner.age.range"]
        cls.Partner = cls.env["res.partner"]
        cls.manager = cls.env["res.users"].create(
            {
                "name": "Cohort Manager",
                "login": "cohort_manager",
                "group_ids": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.env.ref("base.group_partner_manager").id),
                ],
            }
        )

    def _rendered_menu_ids(self, user):
        """The ids the web client actually draws, parents included.

        ``_get_visible_menu_ids`` answers for one menu in isolation and reports the
        Age Ranges entry visible even while its parent is not, so the whole
        branch is dropped from the tree the user sees. Only walking what
        ``load_menus`` returns can catch that.
        """
        menus = self.env["ir.ui.menu"].with_user(user).load_menus(False)
        return {key for key in menus if isinstance(key, int)}

    def test_the_configuration_menu_reaches_the_age_ranges(self):
        """A manager can navigate to the model from Contacts > Configuration."""
        menu = self.env.ref("partner.res_partner_age_range_menu")
        action = self.env.ref("partner.res_partner_age_range_action")

        self.assertEqual(menu.action, action)
        self.assertEqual(
            menu.parent_id, self.env.ref("partner.res_partner_menu_config")
        )
        self.assertEqual(action.res_model, "res.partner.age.range")

    def test_a_partner_manager_is_drawn_the_menu_the_acl_grants(self):
        """The group the ACL empowers must be the group the menu tree admits.

        ``ir.access.csv`` gives ``base.group_partner_manager``
        create/write/unlink on the cohorts. While Configuration was gated on
        ``base.group_system`` that right reached no screen: the branch was
        pruned for exactly the group it was written for, and a manager saw a
        Contacts app holding nothing but Contacts.
        """
        drawn = self._rendered_menu_ids(self.manager)

        self.assertIn(self.env.ref("partner.partner_menu_root").id, drawn)
        self.assertIn(self.env.ref("partner.res_partner_menu_config").id, drawn)
        self.assertIn(
            self.env.ref("partner.res_partner_age_range_menu").id,
            drawn,
            "the cohort menu is not drawn for a partner manager, so the "
            "create/write/unlink the ACL grants them reaches no screen",
        )

    def test_an_internal_user_is_not_drawn_the_configuration_branch(self):
        """The regating widened the audience by one group, not to everyone."""
        plain = self.env["res.users"].create(
            {
                "name": "Plain User",
                "login": "plain_contacts_user",
                "group_ids": [(4, self.env.ref("base.group_user").id)],
            }
        )
        drawn = self._rendered_menu_ids(plain)

        self.assertIn(self.env.ref("partner.res_partner_menu").id, drawn)
        self.assertNotIn(self.env.ref("partner.res_partner_menu_config").id, drawn)
        self.assertNotIn(self.env.ref("partner.res_partner_age_range_menu").id, drawn)

    def test_every_configuration_screen_drawn_to_a_manager_is_one_they_can_save(self):
        """The rule is universal, so the assertion sweeps rather than lists.

        The Configuration branch is gated on the manager, so any entry whose
        model a manager may only *read* has to carry the narrower group itself
        -- otherwise the regating hands out a screen the ACL still refuses to
        save, and the refusal arrives after the edit.

        This was two hardcoded pairs, Industries and Identifier Types, and it
        passed while Countries was drawn to a manager who cannot write
        ``res.country``. A rule stated as a list only ever covers the instances
        somebody thought of; deriving the leaves from the menu tree covers the
        next one too.
        """
        drawn = self._rendered_menu_ids(self.manager)
        config = self.env.ref("partner.res_partner_menu_config")
        leaves = self.env["ir.ui.menu"].search(
            [("id", "child_of", config.id), ("action", "!=", False)]
        )

        swept = []
        for menu in leaves:
            action = menu.action
            if menu.id not in drawn or action._name != "ir.actions.act_window":
                continue
            model = action.res_model
            if not model or model not in self.env:
                continue
            swept.append(menu.complete_name)
            self.assertTrue(
                self.env[model].with_user(self.manager).has_access("write"),
                f"{menu.complete_name} is drawn to a partner manager who "
                f"cannot save {model}",
            )

        self.assertTrue(swept, "the sweep found no screens, so it asserted nothing")

    def test_the_model_has_the_views_its_action_opens(self):
        """`list,form` are declared, so the action does not fall back to a default."""
        action = self.env.ref("partner.res_partner_age_range_action")
        declared = {
            view.type
            for view in self.env["ir.ui.view"].search(
                [("model", "=", "res.partner.age.range")]
            )
        }

        self.assertEqual(action.view_mode, "list,form")
        self.assertLessEqual({"list", "form", "search"}, declared)

    def test_the_access_rule_is_now_exercisable(self):
        """A partner manager can create a cohort through the action's model."""
        cohort = self.AgeRange.with_user(self.manager).create(
            {"name": "Reachable cohort", "min_value": 1600, "max_value": 1700}
        )

        self.assertTrue(cohort.id)

    def test_the_form_offers_the_birthdate_the_cohort_derives_from(self):
        """A classifier whose input no view accepts classifies nothing.

        ``birthdate`` is declared in ``base`` and was shown by no view in this
        repository, so the stored cohort, its group-by, its menu and its demo
        data all stood behind a field the user could not fill. Only
        ``agromarin/marin`` offered a way in, and that is a customer module.
        """
        arch = etree.fromstring(
            self.Partner.get_view(self.env.ref("base.view_partner_form").id)["arch"]
        )
        page = arch.xpath("//page[@name='personal_information_page']")
        self.assertTrue(page, "the Contacts form offers no personal information page")

        offered = [field.get("name") for field in page[0].iter("field")]
        self.assertEqual(set(offered), {"gender", "birthdate", "age", "age_range_id"})
        self.assertEqual(
            len(offered),
            len(set(offered)),
            "a field is placed twice on the page: two modules each xpath their "
            "own copy of it, which is what owning the placement here prevents",
        )

    def test_a_cohort_can_be_filtered_and_not_only_grouped(self):
        """Grouping is the analyst's tool; filtering is the user's."""
        arch = etree.fromstring(
            self.env.ref("base.view_res_partner_filter").get_combined_arch()
        )
        self.assertTrue(arch.xpath("//field[@name='age_range_id']"))
        self.assertTrue(arch.xpath("//field[@name='age']"))
        self.assertTrue(arch.xpath("//filter[@name='group_age_range']"))

    def test_contacts_can_be_grouped_by_their_cohort(self):
        """The stored cohort is a usable group-by, which is why it is offered."""
        self.AgeRange.search([]).active = False
        cohort = self.AgeRange.create(
            {"name": "Grouped cohort", "min_value": 1700, "max_value": 1800}
        )
        partner = self.Partner.create(
            {"name": "Grouped contact", "birthdate": "1750-03-02"}
        )

        self.assertEqual(partner.age_range_id, cohort)
        groups = self.Partner._read_group(
            [("id", "=", partner.id)], groupby=["age_range_id"]
        )
        self.assertEqual(groups, [(cohort,)])
