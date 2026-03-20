import { patch } from "@web/core/utils/patch";
import {
    LeadGenerationDropdown,
    MODULE_STATUS
} from "@crm/components/lead_generation_dropdown/lead_generation_dropdown";

patch(LeadGenerationDropdown.prototype, {
    setup() {
        super.setup();
        const iapElement = this.state.dropdownContentElements.find(
            element => element.moduleXmlId === 'base.module_crm_iap_mine'
        );
        Object.assign(iapElement, {
            onClick: () => this.openLeadGenerationForm(),
            status: MODULE_STATUS.INSTALLED,
            model: "crm.iap.lead.mining.request",
        });
    },

    async openLeadGenerationForm() {
        const action = await this.orm.call("crm.lead", "action_generate_leads", []);
        this.action.doAction(action);
    }
});
