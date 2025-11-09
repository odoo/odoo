import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class CustomerFilterOption extends BaseOptionComponent {
    static template = "website_customer.CustomerFilterOption";
    static selector = "main:not(:has(#oe_structure_website_crm_partner_assign_layout_1)):has(.o_wcrm_filters_top)";
    static groups = ["website.group_website_designer"];
    static title = _t("Customers Page");
    static editableOnly = false;

    setup() {
        super.setup();
        this.googleMapsService = useService("google_maps");
        onWillStart(async () => {
            this.hasGoogleMapsApiKey = !!(await this.googleMapsService.getGMapsAPIKey());
        });
    }
}
