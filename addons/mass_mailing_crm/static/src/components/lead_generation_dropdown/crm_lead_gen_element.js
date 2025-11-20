import { patch } from "@web/core/utils/patch";
import {
    LeadGenerationDropdown,
    MODULE_STATUS
} from "@crm/components/lead_generation_dropdown/lead_generation_dropdown";

patch(LeadGenerationDropdown.prototype, {
    setup() {
        super.setup();
        const mailingElement = this.state.dropdownContentElements.find(
            element => element.moduleXmlId === 'base.module_mass_mailing'
        );
        Object.assign(mailingElement, {
            onClick: () => this.openMailTemplate(),
            status: MODULE_STATUS.INSTALLED,
            model: 'mailing.mailing',
        });
    },
    async openMailTemplate() {
        const action = await this.orm.call(
             'mailing.mailing',
             'action_create_mailing_template_with_leads',
             [],
        );
        await this.action.doAction(action);
    }
});
