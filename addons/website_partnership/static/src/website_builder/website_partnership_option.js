import { BaseOptionComponent } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";

export class WebsitePartnersPage extends BaseOptionComponent {
    static template = "website_partnership.PartnershipPageOption";
    static selector = "main:has(#oe_structure_website_partnership_layout_1)";
    static title = _t("Partner Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}
