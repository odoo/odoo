import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class WebsiteCRMPartnerPageOption extends Plugin {
    static id = "websiteCRMPartnerPageOption";

    resources = {
        builder_options: [
            {
                template: "website_crm_partner_assign.PartnerPageOption",
                selector: "main:has(#oe_structure_website_crm_partner_assign_layout_1):not(:has(.o_wcrm_filters_top))",
                title: _t("Partner Page"),
                editableOnly: false,
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteCRMPartnerPageOption.id, WebsiteCRMPartnerPageOption);
