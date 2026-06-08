import { patch } from "@web/core/utils/patch";
import {
    LeadGenerationDropdown,
    MODULE_STATUS
} from "@crm/components/lead_generation_dropdown/lead_generation_dropdown";

patch(LeadGenerationDropdown.prototype, {
    setup() {
        super.setup();
        const surveyElement = this.state.dropdownContentElements.find(element => element.moduleXmlId === 'base.module_survey');
        Object.assign(surveyElement, {
            onClick: () => this.createLeadGenerationSurvey(),
            status: MODULE_STATUS.INSTALLED,
            model: 'survey.survey',
        });
    },
    async createLeadGenerationSurvey() {
        const action = await this.orm.call(
             'survey.survey',
             'action_load_survey_template_sample',
             ['lead_qualification'],
        );
        await this.action.doAction(action);
    }
});
