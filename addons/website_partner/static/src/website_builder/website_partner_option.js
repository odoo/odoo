import { BaseOptionComponent } from "@html_builder/core/utils";
import { useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class WebsiteCRMPartnersPage extends BaseOptionComponent {
    static template = "website_partner.PartnersPageOption";

    setup() {
        super.setup();
        this.googleMaps = useService("google_maps");
        this.state = useState({
            has_google_maps_api_key: false,
        });

        onWillStart(async () => {
            this.state.has_google_maps_api_key = !!(await this.googleMaps.getGMapsAPIKey(false));
        });
    }
}
