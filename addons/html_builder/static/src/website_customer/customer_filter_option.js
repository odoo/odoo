import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CustomerFilterOption extends BaseOptionComponent {
    static template = "website_customer.CustomerFilterOption";

    setup() {
        super.setup();
        this.googleMapsService = useService("google_maps");
        onWillStart(async () => {
            this.hasGoogleMapsApiKey = !!(await this.googleMapsService.getGMapsAPIKey());
        });
    }
}
