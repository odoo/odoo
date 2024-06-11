/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { renderToElement } from "@web/core/utils/render";
import SESSION_CHART_COLORS from "@survey/js/survey_session_colors";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
const { DateTime } = luxon;

publicWidget.registry.SurveySessionTextAnswers = publicWidget.Widget.extend({
    init: function (parent, options) {
        this._super.apply(this, arguments);

        this.answerIds = [];
        this.questionType = options.questionType;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Adds the attendees answers on the screen.
     * This is used for char_box/date and datetime questions.
     *
     * We use some tricks with jQuery for wow effect:
     * - force a width on the external div container, to reserve space for that answer
     * - set the actual width of the answer, and enable a css width animation
     * - set the opacity to 1, and enable a css opacity animation
     *
     * @param {Array} inputLineValues array of survey.user_input.line records in the form
     *   {id: line.id, value: line.[value_char_box/value_date/value_datetime]}
     */
    updateTextAnswers: function (inputLineValues) {
        var self = this;

        inputLineValues.forEach(function (inputLineValue) {
            if (!self.answerIds.includes(inputLineValue.id) && inputLineValue.value) {
                var textValue = inputLineValue.value;
                if (self.questionType === 'char_box') {
                    textValue = textValue.length > 25 ?
                        textValue.substring(0, 22) + '...' :
                        textValue;
                } else if (self.questionType === 'date') {
                    textValue = formatDate(DateTime.fromFormat(textValue, "yyyy-MM-dd"));
                } else if (self.questionType === 'datetime') {
                    textValue = formatDateTime(
                        DateTime.fromFormat(textValue, "yyyy-MM-dd HH:mm:ss")
                    );
                }

                var $textAnswer = $(renderToElement('survey.survey_session_text_answer', {
                    value: textValue,
                    borderColor: `rgb(${SESSION_CHART_COLORS[self.answerIds.length % 10]})`
                }));
                self.$el.append($textAnswer);
                var spanWidth = $textAnswer.find('span').width();
                var calculatedWidth = `calc(${spanWidth}px + 1.2rem)`;
                $textAnswer.css('width', calculatedWidth);
                setTimeout(function () {
                    // setTimeout to force jQuery rendering
                    $textAnswer.find('.o_survey_session_text_answer_container')
                        .css('width', calculatedWidth)
                        .css('opacity', '1');
                }, 1);
                self.answerIds.push(inputLineValue.id);
            }
        });
    },
});

export default publicWidget.registry.SurveySessionTextAnswers;
