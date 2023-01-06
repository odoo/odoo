/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { sprintf } from '@web/core/utils/strings';
import { standardWidgetProps} from "@web/views/widgets/standard_widget_props";

const { Component, useEffect, useRef, useState } = owl;

export class SurveyQuestionTriggerWidget extends Component {
    setup() {
        super.setup();
        this.button = useRef('survey_question_trigger');
        this.state = useState({
            triggeringQuestionTitle: this.props.record.data.triggering_question_id,
            surveyQuestionTriggerTooltip: "",
            surveyQuestionTriggerError: false
        });
        useEffect(() => {
            if (this.button && this.button.el) {
                this.state.triggeringQuestionTitle = this.props.record.data.triggering_question_id[1];
                if (this.props.record.data.is_placed_before_trigger) {
                    this.state.surveyQuestionTriggerError = true;
                    this.state.surveyQuestionTriggerTooltip = sprintf(
                        _lt('⚠️ This question is positioned before its trigger ("%s") and will be skipped.'),
                        this.state.triggeringQuestionTitle);
                } else if (this.props.record.data.question_selection === "random") {
                    this.state.surveyQuestionTriggerError = true;
                    this.state.surveyQuestionTriggerTooltip = _lt(
                        '⚠️ Conditional display is not available when questions are randomly picked.');
                } else if (!this.props.record.data.triggering_question_id) { //extra-precaution, see `surveyQuestionTriggerError`
                    this.state.surveyQuestionTriggerError = true;
                    this.state.surveyQuestionTriggerTooltip = sprintf(
                        _lt('⚠️ The trigger question configured ("%s") is missing. This trigger will be automatically removed.'),
                        this.state.triggeringQuestionTitle);
                } else {
                    this.state.surveyQuestionTriggerError = false;
                    this.state.surveyQuestionTriggerTooltip = sprintf(_lt('Displayed if "%s: %s"'),
                        this.state.triggeringQuestionTitle, this.props.record.data.triggering_answer_id[1]);
                }
            } else {
                this.state.surveyQuestionTriggerError = false;
                this.state.triggeringQuestionTitle = "";
                this.state.surveyQuestionTriggerTooltip = "";
            }
        });
    }
}

SurveyQuestionTriggerWidget.template = "survey.surveyQuestionTrigger";
SurveyQuestionTriggerWidget.props = {
    ...standardWidgetProps,
};

SurveyQuestionTriggerWidget.displayName = 'Trigger';
SurveyQuestionTriggerWidget.supportedTypes = ['many2one'];

registry.category("view_widgets").add("survey_question_trigger", SurveyQuestionTriggerWidget);
