import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class CRMPartnerAssignGoogleMapsEdit extends Interaction {
	static selector = ".partner_map_button";
    dynamicContent = {
        "_root": {
            "t-att-disabled": () => false,
        },
    }
}

registry
	.category("public.interactions.edit")
	.add("website_crm_partner_assign.crm_partner_assign_google_maps", {
		Interaction: CRMPartnerAssignGoogleMapsEdit,
	});
