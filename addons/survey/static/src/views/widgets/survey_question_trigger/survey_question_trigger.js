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
            surveyQuestionTriggerIconClass: "",
        });
        useEffect(() => {
            if (this.button && this.button.el) {
                this.state.triggeringQuestionTitle = this.props.record.data.triggering_question_id[1];
                const triggerError = this.surveyQuestionTriggerError;
                if (triggerError === "MISPLACED_TRIGGER_WARNING") {
                    this.state.surveyQuestionTriggerTooltip = sprintf(
                        '⚠ ' + _lt('This question is positioned before its trigger ("%s") and will be skipped.'),
                        this.state.triggeringQuestionTitle);
                    this.state.surveyQuestionTriggerIconClass = 'fa-exclamation-triangle text-warning';
                } else if (triggerError === "WRONG_QUESTIONS_SELECTION_WARNING") {
                    this.state.surveyQuestionTriggerTooltip = '⚠ ' + _lt(
                        'Conditional display is not available when questions are randomly picked.');
                    this.state.surveyQuestionTriggerIconClass = 'fa-exclamation-triangle text-warning';
                } else if (triggerError === "MISSING_TRIGGER_ERROR") {
                    // This case must be handled to not temporarily render the "normal" icon if previously
                    // on an error state, which would cause a flicker as the trigger itself will be removed
                    // at next save (auto on survey form and primary list view).
                } else {
                    this.state.surveyQuestionTriggerTooltip = sprintf(_lt('Displayed if "%s: %s"'),
                        this.state.triggeringQuestionTitle, this.props.record.data.triggering_answer_id[1]);
                    this.state.surveyQuestionTriggerIconClass = 'fa-code-fork';
                }
            } else {
                this.state.triggeringQuestionTitle = "";
                this.state.surveyQuestionTriggerTooltip = "";
                this.state.surveyQuestionTriggerIconClass = "";
            }
        });
    }

    /**
     * `surveyQuestionTriggerError` is computed here and does not rely on
     * record data (is_placed_before_trigger) for two linked reasons:
     * 1. Performance: we avoid saving the survey each time a line is moved.
     * 2. Robustness, as sequences values do not always match between server
     * provided values when the records are not saved.
     *
     * @returns { String }
     *   * `""`: No trigger error (also if `triggering_question_id`
     *     field is not set).
     *   * `"MISSING_TRIGGER_ERROR"`: `triggering_question_id` field is set
     *     and trigger record is not found. This can happen when a question
     *     used as trigger is deleted on the client but not yet saved to DB.
     *   * `"MISPLACED_TRIGGER_WARNING"`: a `triggering_question_id` is set
     *     but is positioned after the current record in the list. This can
     *     happen if the triggering or the triggered question is moved.
     *   * `"WRONG_QUESTIONS_SELECTION_WARNING"`: a `triggering_question_id`
     *     is set but the survey is configured to randomize questions asked
     *     mode which ignores the triggers. This can happen if the survey mode
     *     is changed after triggers are set.
     */
    get surveyQuestionTriggerError() {
        const record = this.props.record;
        if (!record.data.triggering_question_id) {
            return "";
        }
        const triggerId = record.data.triggering_question_id[0];
        let triggerRecord;
        if (this.props.isSurveyForm) { // embedded list
            triggerRecord = record.model.root.data.question_and_page_ids.records.find(rec => rec.data.id === triggerId);
        } else {
            triggerRecord = record.model.root.records.find(rec => rec.resId === triggerId);
        }

        if (!triggerRecord) {
            return "MISSING_TRIGGER_ERROR";
        }
        if (record.data.questions_selection === 'random') {
            return "WRONG_QUESTIONS_SELECTION_WARNING";
        }
        if (record.data.sequence < triggerRecord.data.sequence ||
            (record.data.sequence === triggerRecord.data.sequence && record.data.id < triggerId)) {
            return "MISPLACED_TRIGGER_WARNING";
        }
        return "";
    }
}

SurveyQuestionTriggerWidget.template = "survey.surveyQuestionTrigger";
SurveyQuestionTriggerWidget.props = {
    ...standardWidgetProps,
    isSurveyForm: { type: Boolean, optional: true },
};

SurveyQuestionTriggerWidget.defaultProps = {
    isSurveyForm: false
};

SurveyQuestionTriggerWidget.extractProps = ({ attrs }) => {
    return {
        isSurveyForm: attrs.options.isSurveyForm
    };
};

SurveyQuestionTriggerWidget.displayName = 'Trigger';
SurveyQuestionTriggerWidget.supportedTypes = ['many2one'];

registry.category("view_widgets").add("survey_question_trigger", SurveyQuestionTriggerWidget);
