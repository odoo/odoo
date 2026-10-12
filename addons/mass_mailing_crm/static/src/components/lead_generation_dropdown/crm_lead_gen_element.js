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
        const context = {};
        const default_team_id = this.env.searchModel.context.default_team_id;
        if (default_team_id) {
            context.default_team_id = default_team_id;
        }
        const action = await this.orm.call(
            'mailing.mailing',
            'action_create_mailing_template_with_leads',
            [],
            { context },
        );
        await this.action.doAction(action);
    }
});
