import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { WebsitePartnersPage } from "./website_partnerhip_option";

class WebsitePartnershipPageOption extends Plugin {
    static id = "WebsitePartnershipPageOption";

    resources = {
        builder_options: [
            {
                OptionComponent: WebsitePartnersPage,
                selector: "main:has(#oe_structure_website_partnership_layout_1)",
                title: _t("Partners Page"),
                editableOnly: false,
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsitePartnershipPageOption.id, WebsitePartnershipPageOption);
