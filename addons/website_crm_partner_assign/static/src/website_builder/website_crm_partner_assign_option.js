import { BaseOptionComponent } from "@html_builder/core/utils";
import { useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class WebsiteCRMPartnersPageOption extends BaseOptionComponent {
    static id = "website_crm_partners_page_option"
    static template = "website_crm_partner_assign.PartnersPageOption";

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

registry.category("builder-options").add(WebsiteCRMPartnersPageOption.id, WebsiteCRMPartnersPageOption);

