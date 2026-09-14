from odoo import Command
from odoo.tests.common import HttpCase, TransactionCase, new_test_user

DISABLED_MAIL_CONTEXT = {
    "tracking_disable": True,
    "mail_create_nolog": True,
    "mail_create_nosubscribe": True,
    "mail_notrack": True,
    "no_reset_password": True,
}


class BaseCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env = cls.env["base"].with_context(**cls.default_env_context()).env

        independent_user = cls.setup_independent_user()
        if independent_user:
            cls.env = cls.env(user=independent_user)
            cls.user = cls.env.user
        else:
            cls.env.user.group_ids += cls.get_default_groups()

        independent_company = cls.setup_independent_company()
        if independent_company:
            cls.env.user.company_id = independent_company
            cls.env.user.company_ids = [Command.set(independent_company.ids)]
        else:
            cls.setup_main_company()

        cls.company = cls.env.company
        cls.currency = cls.env.company.currency_id

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
            }
        )

        cls.group_portal = cls.quick_ref("base.group_portal")
        cls.group_user = cls.quick_ref("base.group_user")
        cls.group_system = cls.quick_ref("base.group_system")

    @classmethod
    def default_env_context(cls):
        return {**DISABLED_MAIL_CONTEXT}

    @classmethod
    def setup_other_currency(cls, code, **kwargs):
        rates = kwargs.pop("rates", [])
        currency = cls._enable_currency(code)
        currency.rate_ids.unlink()
        currency.write(
            {
                "active": True,
                "rate_ids": [
                    Command.create(
                        {
                            "name": rate_date,
                            "rate": rate,
                            "company_id": cls.env.company.id,
                        }
                    )
                    for rate_date, rate in rates
                ],
                **kwargs,
            }
        )
        return currency

    @classmethod
    def setup_independent_company(cls, **kwargs):
        return None

    @classmethod
    def setup_independent_user(cls):
        return None

    @classmethod
    def get_default_groups(cls):
        return cls.env.ref("base.group_user")

    @classmethod
    def setup_main_company(cls, currency_code="USD"):
        cls._use_currency(cls.env.company, currency_code)

    @classmethod
    def _enable_currency(cls, currency_code):
        currency = (
            cls.env["res.currency"]
            .with_context(active_test=False)
            .search(
                [("name", "=", currency_code.upper())],
                limit=1,
            )
        )
        currency.action_unarchive()
        return currency

    @classmethod
    def _use_currency(cls, company, currency_code):
        currency = cls._enable_currency(currency_code)
        if company.currency_id != currency:
            cls.env.transaction.cache.set(
                cls.env.company,
                type(cls.env.company).currency_id,
                currency.id,
                dirty=True,
            )

    @classmethod
    def _create_partner(cls, **create_values):
        return cls.env["res.partner"].create(
            {
                "name": "Test Partner",
                "company_id": False,
                **create_values,
            }
        )

    @classmethod
    def _create_company(cls, **create_values):
        company = cls.env["res.company"].create(
            {
                "name": "Test Company",
                **create_values,
            }
        )
        cls.env.user.company_ids = [Command.link(company.id)]
        return company

    @classmethod
    def _create_new_internal_user(cls, **kwargs):
        return new_test_user(
            cls.env,
            **({"login": "internal_user"} | kwargs),
        )

    @classmethod
    def _create_new_portal_user(cls, **kwargs):
        return new_test_user(
            cls.env,
            groups="base.group_portal",
            **({"login": "portal_user"} | kwargs),
        )

    @classmethod
    def quick_ref(cls, xmlid):
        model, id = cls.env["ir.model.data"]._xmlid_to_res_model_res_id(xmlid)
        return cls.env[model].browse(id)


class _SeededUserCase:
    @classmethod
    def _rename_admin_partner(cls):
        return False

    @classmethod
    def _seed_user(cls, login, groups, partner_values, create_context=None):
        if cls._rename_admin_partner():
            cls.env.ref("base.partner_admin").write({"name": "Mitchell Admin"})

        user = cls.env["res.users"].sudo().search([("login", "=", login)])
        user = user.with_env(cls.env)
        partner = user.partner_id

        if not user:
            cls.env["ir.config_parameter"].sudo().set_param(
                "auth_password_policy.minlength", 4
            )
            partner = cls.env["res.partner"].create(partner_values)
            user = (
                cls.env["res.users"]
                .with_context(**(create_context or {}))
                .create(
                    {
                        "login": login,
                        "password": login,
                        "partner_id": partner.id,
                        "group_ids": [Command.set([cls.env.ref(g).id for g in groups])],
                    }
                )
            )
        return user, partner


class _UserDemoCase(_SeededUserCase):
    @classmethod
    def _demo_partner_values(cls):
        return {"name": "Marc Demo", "email": "mark.brown23@example.com"}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_demo, cls.partner_demo = cls._seed_user(
            "demo",
            ("base.group_user", "base.group_partner_manager"),
            cls._demo_partner_values(),
        )


class _UserPortalCase(_SeededUserCase):
    @classmethod
    def _portal_partner_values(cls):
        return {"name": "Joel Willis", "email": "joel.willis63@example.com"}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_portal, cls.partner_portal = cls._seed_user(
            "portal",
            ("base.group_portal",),
            cls._portal_partner_values(),
            create_context={"no_reset_password": True},
        )


class TransactionCaseWithUserDemo(_UserDemoCase, TransactionCase):
    @classmethod
    def _rename_admin_partner(cls):
        return True


class HttpCaseWithUserDemo(_UserDemoCase, HttpCase):
    @classmethod
    def _rename_admin_partner(cls):
        return True

    @classmethod
    def _demo_partner_values(cls):
        return {**super()._demo_partner_values(), "tz": "UTC"}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_admin = cls.env.ref("base.user_admin")
        cls.user_admin.write({"name": "Mitchell Admin"})
        cls.partner_admin = cls.user_admin.partner_id


class SavepointCaseWithUserDemo(_UserDemoCase, TransactionCase):
    @classmethod
    def _load_partners_set(cls):
        cls.partner_category = cls.env["res.partner.tag"].create(
            {
                "name": "Sellers",
                "color": 2,
            }
        )
        cls.partner_category_child_1 = cls.env["res.partner.tag"].create(
            {
                "name": "Office Supplies",
                "parent_id": cls.partner_category.id,
            }
        )
        cls.partner_category_child_2 = cls.env["res.partner.tag"].create(
            {
                "name": "Desk Manufacturers",
                "parent_id": cls.partner_category.id,
            }
        )

        cls.partners = cls.env["res.partner"].create(
            [
                {
                    "name": "Inner Works",
                    "state_id": cls.env.ref("base.state_us_1").id,
                    "tag_ids": [
                        Command.set(
                            [
                                cls.partner_category_child_1.id,
                                cls.partner_category_child_2.id,
                            ]
                        )
                    ],
                    "child_ids": [
                        Command.create(
                            {
                                "name": "Sheila Ruiz",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Wyatt Howard",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Austin Kennedy",
                            }
                        ),
                    ],
                },
                {
                    "name": "Pepper Street",
                    "state_id": cls.env.ref("base.state_us_2").id,
                    "child_ids": [
                        Command.create(
                            {
                                "name": "Liam King",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Craig Richardson",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Adam Cox",
                            }
                        ),
                    ],
                },
                {
                    "name": "AnalytIQ",
                    "state_id": cls.env.ref("base.state_us_3").id,
                    "child_ids": [
                        Command.create(
                            {
                                "name": "Pedro Boyd",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Landon Roberts",
                                "company_id": cls.env.ref("base.main_company").id,
                            }
                        ),
                        Command.create(
                            {
                                "name": "Leona Shelton",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Scott Kim",
                            }
                        ),
                    ],
                },
                {
                    "name": "Urban Trends",
                    "state_id": cls.env.ref("base.state_us_4").id,
                    "tag_ids": [
                        Command.set(
                            [
                                cls.partner_category_child_1.id,
                                cls.partner_category_child_2.id,
                            ]
                        )
                    ],
                    "child_ids": [
                        Command.create(
                            {
                                "name": "Louella Jacobs",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Albert Alexander",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Brad Castillo",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Sophie Montgomery",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Chloe Bates",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Mason Crawford",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Elsie Kennedy",
                            }
                        ),
                    ],
                },
                {
                    "name": "Ctrl-Alt-Fix",
                    "state_id": cls.env.ref("base.state_us_5").id,
                    "child_ids": [
                        Command.create(
                            {
                                "name": "carole miller",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Cecil Holmes",
                            }
                        ),
                    ],
                },
                {
                    "name": "Ignitive Labs",
                    "state_id": cls.env.ref("base.state_us_6").id,
                    "child_ids": [
                        Command.create(
                            {
                                "name": "Jonathan Webb",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Clinton Clark",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Howard Bryant",
                            }
                        ),
                    ],
                },
                {
                    "name": "Amber & Forge",
                    "state_id": cls.env.ref("base.state_us_7").id,
                    "child_ids": [
                        Command.create(
                            {
                                "name": "Mark Webb",
                            }
                        )
                    ],
                },
                {
                    "name": "Rebecca Day",
                    "parent_id": cls.env.ref("base.main_partner").id,
                },
                {
                    "name": "Gabriella Jennings",
                    "parent_id": cls.env.ref("base.main_partner").id,
                },
            ]
        )


class TransactionCaseWithUserPortal(_UserPortalCase, TransactionCase):
    pass


class HttpCaseWithUserPortal(_UserPortalCase, HttpCase):
    pass
