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
        const context = {};
        const default_team_id = this.env.searchModel.context.default_team_id;
        if (default_team_id) {
            context.default_team_id = default_team_id;
        }
        const action = await this.orm.call(
            'survey.survey',
            'action_load_survey_template_sample',
            ['lead_qualification'],
            { context },
        );
        await this.action.doAction(action);
    }
});
