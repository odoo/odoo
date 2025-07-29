import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CustomerFilterOption extends BaseOptionComponent {
    static template = "website_customer.CustomerFilterOption";
    static selector = ".o_wcrm_filters_top";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;

    setup() {
        super.setup();
        this.googleMapsService = useService("google_maps");
        onWillStart(async () => {
            this.hasGoogleMapsApiKey = !!(await this.googleMapsService.getGMapsAPIKey());
        });
    }
}
