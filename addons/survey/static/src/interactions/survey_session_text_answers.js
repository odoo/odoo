import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";
import { Interaction } from "@web/public/interaction";
import SESSION_CHART_COLORS from "@survey/interactions/survey_session_colors";
const { DateTime } = luxon;

export class SurveySessionTextAnswers extends Interaction {
    static selector = ".o_survey_session_text_answers_container";
    dynamicContent = {
        _root: {
            "t-on-updateTextAnswers": this.updateTextAnswers,
        },
    };

    setup() {
        this.answerIds = [];
    }

    /**
     * Adds the attendees answers on the screen.
     * This is used for char_box/date and datetime questions.
     *
     * We use some tricks for wow effect:
     * - force a width on the external div container, to reserve space for that answer
     * - set the actual width of the answer, and enable a css width animation
     * - set the opacity to 1, and enable a css opacity animation
     *
     * @param {CustomEvent} ev Custom event containing the questionType and
     * the array of survey.user_input.line records in the form
     * {id: line.id, value: line.[value_char_box/value_date/value_datetime]}
     */
    updateTextAnswers(ev) {
        const inputLineValues = ev.detail.inputLineValues;
        const questionType = ev.detail.questionType;

        inputLineValues.forEach((inputLineValue) => {
            if (!this.answerIds.includes(inputLineValue.id) && inputLineValue.value) {
                let textValue = inputLineValue.value;
                if (questionType === "date") {
                    textValue = formatDate(DateTime.fromFormat(textValue, "yyyy-MM-dd"));
                } else if (questionType === "datetime") {
                    textValue = formatDateTime(
                        DateTime.fromFormat(textValue, "yyyy-MM-dd HH:mm:ss")
                    );
                }
                const textAnswerEl = renderToElement("survey.survey_session_text_answer", {
                    value: textValue,
                    borderColor: `rgb(${SESSION_CHART_COLORS[this.answerIds.length % 10]})`,
                });
                this.insert(textAnswerEl, this.el);
                const spanWidth = textAnswerEl.querySelector("span").offsetWidth;
                const containerEl = textAnswerEl.querySelector(
                    ".o_survey_session_text_answer_container"
                );
                textAnswerEl.style.width = `calc(${spanWidth}px + 1.2rem)`;
                containerEl.style.width = `calc(${spanWidth}px + 1.2rem)`;
                containerEl.style.opacity = "1";
                this.answerIds.push(inputLineValue.id);
            }
        });
    }
}

registry
    .category("public.interactions")
    .add("survey.survey_session_text_answers", SurveySessionTextAnswers);
