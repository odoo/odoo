import { BaseOptionComponent } from "@html_builder/core/utils";
import { useState, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class WebsiteCRMPartnersPage extends BaseOptionComponent {
    static template = "website_crm_partner_assign.PartnersPageOption";
    static selector = "main:has(#oe_structure_website_crm_partner_assign_layout_1):has(.o_wcrm_filters_top)";
    static title = _t("Partners Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;

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
