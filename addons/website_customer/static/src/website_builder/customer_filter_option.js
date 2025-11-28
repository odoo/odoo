import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class CustomerFilterOption extends BaseOptionComponent {
    static id = "customer_filter_option";
    static template = "website_customer.CustomerFilterOption";

    setup() {
        super.setup();
        this.googleMapsService = useService("google_maps");
        onWillStart(async () => {
            this.hasGoogleMapsApiKey = !!(await this.googleMapsService.getGMapsAPIKey());
        });
    }
}

registry.category("builder-options").add(CustomerFilterOption.id, CustomerFilterOption);
