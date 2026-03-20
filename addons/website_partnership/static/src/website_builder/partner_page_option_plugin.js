import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class PartnerPageOption extends BaseOptionComponent {
    static template = "website_partnership.PartnerPageOption";
    static selector = "main:has(#oe_structure_website_partnership_partner_1):not(:has(.o_wcrm_filters_top))";
    static title = _t("Partner Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

class WebsitePartnerPageOption extends Plugin {
    static id = "WebsitePartnerPageOption";

    resources = {
        builder_options: [PartnerPageOption],
    };
}

registry
    .category("website-plugins")
    .add(WebsitePartnerPageOption.id, WebsitePartnerPageOption);
