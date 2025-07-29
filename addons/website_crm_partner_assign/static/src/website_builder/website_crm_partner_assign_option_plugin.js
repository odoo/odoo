import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { WebsiteCRMPartnersPage } from "./website_crm_partner_assign_option";

class WebsiteCRMPartnersPageOption extends Plugin {
    static id = "websiteCRMPartnersPageOption";

    resources = {
        builder_options: [
            {
                OptionComponent: WebsiteCRMPartnersPage,
                selector: "main:has(#oe_structure_website_partner_layout_1)",
                title: _t("Partners Page"),
                editableOnly: false,
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteCRMPartnersPageOption.id, WebsiteCRMPartnersPageOption);
