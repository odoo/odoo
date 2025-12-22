/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component, useEffect, useRef, useState } from "@odoo/owl";

export class SurveyQuestionTriggerWidget extends Component {
    static template = "survey.surveyQuestionTrigger";
    static props = {
    ...standardWidgetProps,
    };

    setup() {
        super.setup();
        this.button = useRef('survey_question_trigger');
        this.state = useState({
            surveyIconWarning: false,
            triggerTooltip: "",
        });
        useEffect(() => {
            if (this.button?.el && this.props.record.data.triggering_question_ids.records?.length !== 0) {
                const { triggerError, misplacedTriggerQuestionRecords } = this.surveyQuestionTriggerError;
                if (triggerError === "MISPLACED_TRIGGER_WARNING") {
                    this.state.surveyIconWarning = true;
                    this.state.triggerTooltip = '⚠ ' + _t(
                        'Triggers based on the following questions will not work because they are positioned after this question:\n"%s".',
                        misplacedTriggerQuestionRecords
                            .map((question) => question.data.title)
                            .join('", "')
                    );
                } else if (triggerError === "WRONG_QUESTIONS_SELECTION_WARNING") {
                    this.state.surveyIconWarning = true;
                    this.state.triggerTooltip = '⚠ ' + _t(
                        "Conditional display is not available when questions are randomly picked."
                    );
                } else if (triggerError === "MISSING_TRIGGER_ERROR") {
                    // This case must be handled to not temporarily render the "normal" icon if previously
                    // on an error state, which would cause a flicker as the trigger itself will be removed
                    // at next save (auto on survey form and primary list view).
                } else {
                    this.state.surveyIconWarning = false;
                    this.state.triggerTooltip = _t(
                        'Displayed if "%s".',
                        this.props.record.data.triggering_answer_ids.records
                            .map((answer) => answer.data.display_name)
                            .join('", "'),
                    );
                }
            } else {
                this.state.surveyIconWarning = false;
                this.state.triggerTooltip = "";
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
     * @returns {{ triggerError: String, misplacedTriggerQuestionRecords: Record[] }}
     *   * `""`: No trigger error (also if `triggering_question_id`
     *     field is not set).
     *   * `"MISSING_TRIGGER_ERROR"`: `triggering_questions_ids` field is set
     *     but trigger record is not found. This can happen if all questions
     *     used as triggers are deleted on the client but not yet saved to DB.
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
        if (!record.data.triggering_question_ids.records.length) {
            return { triggerError: "", misplacedTriggerQuestionRecords: [] };
        }
        if (this.props.record.data.questions_selection === 'random') {
            return { triggerError: 'WRONG_QUESTIONS_SELECTION_WARNING', misplacedTriggerQuestionRecords: [] };
        }

        const missingTriggerQuestionsIds = [];
        let triggerQuestionsRecords = [];
        for (const triggeringQuestion of record.data.triggering_question_ids.records) {
            const triggeringQuestionRecord = record.model.root.data.question_and_page_ids.records.find(
                rec => rec.resId === triggeringQuestion.resId);
            if (triggeringQuestionRecord) {
                triggerQuestionsRecords.push(triggeringQuestionRecord);
            } else {  // Trigger question was deleted from the list
                missingTriggerQuestionsIds.push(triggeringQuestion.resId);
            }
        }

        if (missingTriggerQuestionsIds.length === this.props.record.data.triggering_question_ids.records.length) {
            return { triggerError: 'MISSING_TRIGGER_ERROR', misplacedTriggerQuestionRecords: [] }; // only if all are missing
        }
        const misplacedTriggerQuestionRecords = [];
        for (const triggerQuestionRecord of triggerQuestionsRecords) {
            if (record.data.sequence < triggerQuestionRecord.data.sequence ||
                (record.data.sequence === triggerQuestionRecord.data.sequence && record.resId < triggerQuestionRecord.resId)) {
                misplacedTriggerQuestionRecords.push(triggerQuestionRecord);
            }
        }
        return {
            triggerError: misplacedTriggerQuestionRecords.length ? "MISPLACED_TRIGGER_WARNING" : "",
            misplacedTriggerQuestionRecords: misplacedTriggerQuestionRecords,
        };
    }
}

export const surveyQuestionTriggerWidget = {
    component: SurveyQuestionTriggerWidget,
    fieldDependencies: [
        { name: "triggering_question_ids", type: "many2one" },
        { name: "triggering_answer_ids", type: "many2one" },
    ],
};
registry.category("view_widgets").add("survey_question_trigger", surveyQuestionTriggerWidget);
