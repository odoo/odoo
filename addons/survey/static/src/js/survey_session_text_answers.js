odoo.define('survey.session_text_answers', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var core = require('web.core');
var time = require('web.time');
var SESSION_CHART_COLORS = require('survey.session_colors');

var QWeb = core.qweb;

publicWidget.registry.SurveySessionTextAnswers = publicWidget.Widget.extend({
    xmlDependencies: ['/survey/static/src/xml/survey_session_text_answer_template.xml'],
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
                    textValue = moment(textValue).format(time.getLangDateFormat());
                } else if (self.questionType === 'datetime') {
                    textValue = moment(textValue).format(time.getLangDatetimeFormat());
                }

                var $textAnswer = $(QWeb.render('survey.survey_session_text_answer', {
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

return publicWidget.registry.SurveySessionTextAnswers;

});
