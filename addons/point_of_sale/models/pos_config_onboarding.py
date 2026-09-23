from odoo import _, api, models
from odoo.tools import convert

from ..tools import debug_log as dbg


class PosConfigOnboarding(models.Model):
    _inherit = "pos.config"

    def get_record_by_ref(self, recordRefs):
        return [
            self.env.ref(record).id
            for record in recordRefs
            if self.env.ref(record, raise_if_not_found=False)
        ]

    def load_demo_data(self):
        xml_id = (
            self.get_external_id().get(self.id) or self._get_default_demo_data_xml_id()
        )
        loaders = self._get_demo_data_loader_methods()
        dbg.lifecycle.debug(
            "[config:%s] load_demo_data: xml_id=%s loaders=%s",
            self.id,
            xml_id,
            list(loaders),
        )
        for prefix, loader in loaders.items():
            if xml_id.startswith(prefix):
                return loader(True)
        return loaders.get(
            self._get_default_demo_data_xml_id(),
            self._load_onboarding_furniture_demo_data,
        )(True)

    def _get_demo_data_loader_methods(self):
        return {
            "point_of_sale.pos_config_clothes": self._load_onboarding_clothes_demo_data,
            "point_of_sale.pos_config_bakery": self._load_onboarding_bakery_demo_data,
            "point_of_sale.pos_config_main": self._load_onboarding_furniture_demo_data,
        }

    def _get_default_demo_data_xml_id(self):
        return "point_of_sale.pos_config_main"

    @api.model
    def load_onboarding_clothes_scenario(self, with_demo_data=True):
        journal, payment_methods_ids = self._create_journal_and_payment_methods(
            cash_journal_vals={
                "name": _("Cash Clothes Shop"),
                "show_on_dashboard": False,
            }
        )
        config = self.env["pos.config"].create(
            [
                {
                    "name": _("Clothes Shop"),
                    "company_id": self.env.company.id,
                    "journal_id": journal.id,
                    "payment_method_ids": payment_methods_ids,
                }
            ]
        )
        self.env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": self._get_suffixed_ref_name(
                        "point_of_sale.pos_config_clothes"
                    ),
                    "record": config,
                    "noupdate": True,
                }
            ]
        )
        config._load_onboarding_clothes_demo_data(with_demo_data)
        return {"config_id": config.id}

    def _load_onboarding_clothes_demo_data(self, with_demo_data=True):
        self.check_singleton()
        convert.convert_file(
            self._get_env_with_clean_context(),
            "point_of_sale",
            "data/scenarios/clothes_category_data.xml",
            idref=None,
            mode="init",
            noupdate=True,
        )
        if with_demo_data:
            product_module = self.env["ir.module.module"].search(
                [("name", "=", "product")]
            )
            if not product_module.demo:
                convert.convert_file(
                    self._get_env_with_clean_context(),
                    "product",
                    "demo/product_attribute_demo.xml",
                    idref=None,
                    mode="init",
                    noupdate=True,
                )
            convert.convert_file(
                self._get_env_with_clean_context(),
                "point_of_sale",
                "data/scenarios/clothes_data.xml",
                idref=None,
                mode="init",
                noupdate=True,
            )
        clothes_categories = self.get_record_by_ref(
            [
                "point_of_sale.pos_category_upper",
                "point_of_sale.pos_category_lower",
                "point_of_sale.pos_category_others",
            ]
        )
        if clothes_categories:
            self.limit_categories = True
            self.iface_available_categ_ids = clothes_categories

    @api.model
    def load_onboarding_bakery_scenario(self, with_demo_data=True):
        journal, payment_methods_ids = self._create_journal_and_payment_methods(
            cash_journal_vals={"name": _("Cash Bakery"), "show_on_dashboard": False}
        )
        config = self.env["pos.config"].create(
            {
                "name": _("Bakery Shop"),
                "company_id": self.env.company.id,
                "journal_id": journal.id,
                "payment_method_ids": payment_methods_ids,
            }
        )
        self.env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": self._get_suffixed_ref_name(
                        "point_of_sale.pos_config_bakery"
                    ),
                    "record": config,
                    "noupdate": True,
                }
            ]
        )
        config._load_onboarding_bakery_demo_data(with_demo_data)
        return {"config_id": config.id}

    def _load_onboarding_bakery_demo_data(self, with_demo_data=True):
        self.check_singleton()
        convert.convert_file(
            self._get_env_with_clean_context(),
            "point_of_sale",
            "data/scenarios/bakery_category_data.xml",
            idref=None,
            mode="init",
            noupdate=True,
        )
        if with_demo_data:
            convert.convert_file(
                self._get_env_with_clean_context(),
                "point_of_sale",
                "data/scenarios/bakery_data.xml",
                idref=None,
                mode="init",
                noupdate=True,
            )

        bakery_categories = self.get_record_by_ref(
            [
                "point_of_sale.pos_category_breads",
                "point_of_sale.pos_category_pastries",
            ]
        )
        if bakery_categories:
            self.limit_categories = True
            self.iface_available_categ_ids = bakery_categories

    @api.model
    def load_onboarding_furniture_scenario(self, with_demo_data=True):
        journal, payment_methods_ids = self._create_journal_and_payment_methods(
            cash_ref="point_of_sale.cash_payment_method_furniture",
            cash_journal_vals={
                "name": _("Cash Furn. Shop"),
                "show_on_dashboard": False,
            },
        )
        config = self.env["pos.config"].create(
            [
                {
                    "name": _("Furniture Shop"),
                    "company_id": self.env.company.id,
                    "journal_id": journal.id,
                    "payment_method_ids": payment_methods_ids,
                }
            ]
        )
        self.env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": self._get_suffixed_ref_name(
                        "point_of_sale.pos_config_main"
                    ),
                    "record": config,
                    "noupdate": True,
                }
            ]
        )
        config._load_onboarding_furniture_demo_data(with_demo_data)
        existing_session = self.env.ref(
            "point_of_sale.pos_closed_session_2", raise_if_not_found=False
        )
        if (
            with_demo_data
            and self.env.company.id == self.env.ref("base.main_company").id
            and not existing_session
        ):
            convert.convert_file(
                self._get_env_with_clean_context(),
                "point_of_sale",
                "demo/orders_demo.xml",
                idref=None,
                mode="init",
                noupdate=True,
            )
        return {"config_id": config.id}

    def _load_onboarding_furniture_demo_data(self, with_demo_data=False):
        self.check_singleton()
        convert.convert_file(
            self._get_env_with_clean_context(),
            "point_of_sale",
            "data/scenarios/furniture_category_data.xml",
            idref=None,
            mode="init",
            noupdate=True,
        )
        if with_demo_data:
            product_module = self.env["ir.module.module"].search(
                [("name", "=", "product")]
            )
            if not product_module.demo:
                convert.convert_file(
                    self._get_env_with_clean_context(),
                    "product",
                    "demo/product_category_demo.xml",
                    idref=None,
                    mode="init",
                    noupdate=True,
                )
                convert.convert_file(
                    self._get_env_with_clean_context(),
                    "product",
                    "demo/product_attribute_demo.xml",
                    idref=None,
                    mode="init",
                    noupdate=True,
                )
                convert.convert_file(
                    self._get_env_with_clean_context(),
                    "product",
                    "demo/product_demo.xml",
                    idref=None,
                    mode="init",
                    noupdate=True,
                )
            convert.convert_file(
                self._get_env_with_clean_context(),
                "point_of_sale",
                "data/scenarios/furniture_data.xml",
                idref=None,
                mode="init",
                noupdate=True,
            )

        furniture_categories = self.get_record_by_ref(
            [
                "point_of_sale.pos_category_miscellaneous",
                "point_of_sale.pos_category_desks",
                "point_of_sale.pos_category_chairs",
            ]
        )
        if furniture_categories:
            self.limit_categories = True
            self.iface_available_categ_ids = furniture_categories

    @api.model
    def load_onboarding_retail_scenario(self, with_demo_data=False):
        journal, payment_methods_ids = self._create_journal_and_payment_methods(
            cash_journal_vals={
                "name": _("Cash %s", self.env.company.name),
                "show_on_dashboard": False,
            },
        )
        config = self.env["pos.config"].create(
            [
                {
                    "name": self.env.company.name,
                    "company_id": self.env.company.id,
                    "journal_id": journal.id,
                    "payment_method_ids": payment_methods_ids,
                }
            ]
        )
        self.env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": self._get_suffixed_ref_name(
                        "point_of_sale.pos_config_retail"
                    ),
                    "record": config,
                    "noupdate": True,
                }
            ]
        )
        return {"config_id": config.id}

    def _get_suffixed_ref_name(self, ref_name):
        main_company = self.env.ref("base.main_company", raise_if_not_found=False)
        if main_company and self.env.company.id == main_company.id:
            return ref_name
        else:
            dbg.logic.debug(
                "onboarding ref %s suffixed for company %s",
                ref_name,
                self.env.company.id,
            )
            return f"{ref_name}_{self.env.company.id}"

    def _get_env_with_clean_context(self):
        safe_context = {}
        if "allowed_company_ids" in self.env.context:
            safe_context["allowed_company_ids"] = self.env.context[
                "allowed_company_ids"
            ]
        return self.env(context=safe_context)
