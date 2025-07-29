import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { WebsitePartnersPage } from "./website_partner_option";

class WebsitePartnersPageOption extends Plugin {
    static id = "WebsitePartnersPageOption";

    resources = {
        builder_options: [
            {
                OptionComponent: WebsitePartnersPage,
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
    .add(WebsitePartnersPageOption.id, WebsitePartnersPageOption);
