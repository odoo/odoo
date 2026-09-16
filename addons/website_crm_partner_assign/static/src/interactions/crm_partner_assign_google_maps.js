import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class CRMPartnerAssignGoogleMapsEdit extends Interaction {
	static selector = ".partner_view_buttons";
	dynamicContent = {
		_root: {
			"t-att-class": () => ({ "d-none": false }),
		},
	};
}

registry
	.category("public.interactions.edit")
	.add("website_crm_partner_assign.crm_partner_assign_google_maps", {
		Interaction: CRMPartnerAssignGoogleMapsEdit,
	});
