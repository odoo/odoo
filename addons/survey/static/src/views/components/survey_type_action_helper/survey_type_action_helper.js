import { useService } from '@web/core/utils/hooks';
import { Component, onWillStart } from '@odoo/owl';

export class SurveyTypeActionHelper extends Component {
    static template = 'survey.SurveyTypeActionHelper';
    static props = {};

    setup() {
        this.orm = useService('orm');
        this.action = useService('action');

        onWillStart(async () => {
            this.surveyTypeTemplateData = await this.orm.call(
                'survey.survey',
                'get_survey_type_templates_data',
                []
            );
        });
    }

    async onStartFromScratchClick() {
        const action = await this.orm.call(
            'survey.survey',
            'action_load_sample_custom',
            [],
        );
        this.action.doAction(action);
    }

    async onTemplateClick(templateInfo) {
        const action = await this.orm.call(
            'survey.survey',
            'action_setup_survey_type_template',
            [templateInfo.template_key],
        );
        this.action.doAction(action);
    }
};
