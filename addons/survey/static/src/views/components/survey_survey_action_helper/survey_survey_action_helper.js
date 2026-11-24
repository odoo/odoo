import { useService } from '@web/core/utils/hooks';
import { Component, onWillStart, proxy } from '@odoo/owl';

export class SurveySurveyActionHelper extends Component {
    static template = 'survey.SurveySurveyActionHelper';

    setup() {
        this.orm = useService('orm');
        this.action = useService('action');

        this.state = proxy({ surveyTemplateData: {} });

        onWillStart(async () => {
            this.state.surveyTemplateData = await this.orm
                .cache({
                    type: 'disk',
                    update: 'always',
                    callback: (result, hasChanged) => {
                        if (hasChanged) {
                            this.state.surveyTemplateData = result;
                        }
                    },
                })
                .call('survey.survey', 'get_survey_templates_data', []);
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
