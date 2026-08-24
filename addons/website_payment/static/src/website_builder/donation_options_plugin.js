import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class WebsiteDonationFieldsPageOption extends Plugin {
    static id = "WebsiteDonationFieldsPageOption";

    resources = {
        builder_options: [
            {
                selector: "main:has(#oe_structure_website_payment_donation_1)",
                title: _t("Donation Fields"),
                editableOnly: false,
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteDonationFieldsPageOption.id, WebsiteDonationFieldsPageOption);
