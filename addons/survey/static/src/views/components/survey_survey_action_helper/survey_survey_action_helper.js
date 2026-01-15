import { useService } from '@web/core/utils/hooks';
import { Component, onWillStart } from '@odoo/owl';

export class SurveySurveyActionHelper extends Component {
    static template = 'survey.SurveySurveyActionHelper';
    static props = {};

    setup() {
        this.orm = useService('orm');
        this.action = useService('action');

        onWillStart(async () => {
            this.surveyTemplateData = await this.orm.call(
                'survey.survey',
                'get_survey_templates_data',
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
            'action_load_survey_template_sample',
            [templateInfo.template_key],
        );
        this.action.doAction(action);
    }
};
