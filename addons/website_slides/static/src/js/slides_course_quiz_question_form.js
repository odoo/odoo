/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { rpc } from "@web/core/network/rpc";

/**
 * This Widget is responsible of displaying the question inputs when adding a new question or when updating an
 * existing one. When validating the question it makes an RPC call to the server and trigger an event for
 * displaying the question by the Quiz widget.
 */
var QuestionFormWidget = publicWidget.Widget.extend({
    template: 'slide.quiz.question.input',
    events: {
        'click .o_wslides_js_quiz_validate_question': '_validateQuestion',
        'click .o_wslides_js_quiz_cancel_question': '_cancelValidation',
        'click .o_wslides_js_quiz_comment_answer': '_toggleAnswerLineComment',
        'click .o_wslides_js_quiz_add_answer': '_addAnswerLine',
        'click .o_wslides_js_quiz_remove_answer': '_removeAnswerLine',
        'click .o_wslides_js_quiz_remove_answer_comment': '_removeAnswerLineComment',
        'change .o_wslides_js_quiz_answer_comment > input[type=text]': '_onCommentChanged'
    },

    /**
     * @override
     * @param parent
     * @param options
     */
    init: function (parent, options) {
        this.editedQuestion = options.editedQuestion;
        this.question = options.question || {};
        this.update = options.update;
        this.sequence = options.sequence;
        this.slideId = options.slideId;
        this._super.apply(this, arguments);
    },

    /**
     * @override
     * @returns {*}
     */
    start: function () {
        const self = this;
        return this._super.apply(this, arguments).then(function () {
            self.el.querySelector('.o_wslides_quiz_question input').focus();
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     *
     * @param commentInput
     * @private
     */
    _onCommentChanged: function (event) {
        const input = event.currentTarget;
        const commentIcon = input.closest('.o_wslides_js_quiz_answer').querySelector('.o_wslides_js_quiz_comment_answer');
        if (input.value.trim() !== '') {
            commentIcon.classList.add('text-primary');
            commentIcon.classList.remove('text-muted');
        } else {
            commentIcon.classList.add('text-muted');
            commentIcon.classList.remove('text-primary');
        }
    },

    /**
     * Toggle the input for commenting the answer line which will be
     * seen by the frontend user when submitting the quiz.
     * @param ev
     * @private
     */
    _toggleAnswerLineComment: function (ev) {
        const commentLine = ev.currentTarget.closest('.o_wslides_js_quiz_answer').querySelector('.o_wslides_js_quiz_answer_comment')
        commentLine.classList.toggle('d-none');
        commentLine.querySelector('input[type=text]').focus();
    },

    /**
     * Adds a new answer line after the element the user clicked on
     * e.g. If there is 3 answer lines and the user click on the add
     *      answer button on the second line, the new answer line will
     *      display between the second and the third line.
     * @param ev
     * @private
     */
    _addAnswerLine: function (ev) {
        const answerEl = ev.currentTarget.closest('.o_wslides_js_quiz_answer');
        answerEl.parentNode.insertBefore(renderToElement('slide.quiz.answer.line'), answerEl.nextSibling);
    },

    /**
     * Removes an answer line. Can't remove the last answer line.
     * @param ev
     * @private
     */
    _removeAnswerLine: function (ev) {
        if (this.el.querySelector('.o_wslides_js_quiz_answer').length > 1) {
            ev.currentTarget.closest('.o_wslides_js_quiz_answer').remove();
        }
    },

    /**
     *
     * @param ev
     * @private
     */
    _removeAnswerLineComment: function (ev) {
        const commentLine = ev.currentTarget.closest('.o_wslides_js_quiz_answer_comment');
        commentLine.classList.add('d-none');
        const inputEl = commentLine.querySelector('input[type=text]');
        inputEl.value = '';
        // TODO-visp: Check this also
        inputEl.dispatchEvent(new Event('change'));
    },

    /**
     * Handler when user click on 'Save' or 'Update' buttons.
     * @param ev
     * @private
     */
    _validateQuestion: function (ev) {
        this._createOrUpdateQuestion({
            update: ev.currentTarget.classList.contains('o_wslides_js_quiz_update'),
        });
    },

    /**
     * Handler when user click on the 'Cancel' button.
     * Calls a method from slides_course_quiz.js widget
     * which will handle the reset of the question display.
     * @private
     */
    _cancelValidation: function () {
        this.trigger_up('reset_display', {
            questionFormWidget: this,
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * RPC call to create or update a question.
     * Triggers method from slides_course_quiz.js to
     * correctly display the question.
     * @param options
     * @private
     */
    _createOrUpdateQuestion: async function (options) {
        const form = this.el.querySelector('form');

        if (this._isValidForm(form)) {
            const values = this._serializeForm(form);
            const renderedQuestion = await rpc('/slides/slide/quiz/question_add_or_update', values);

            if (typeof renderedQuestion === 'object' && renderedQuestion.error) {
                const errorEl = this.el.querySelector('.o_wslides_js_quiz_validation_error');
                errorEl.classList.remove('d-none');
                errorEl.querySelector('.o_wslides_js_quiz_validation_error_text').textContent = renderedQuestion.error;
            } else if (options.update) {
                this.el.querySelector('.o_wslides_js_quiz_validation_error').classList.add('d-none');
                this.trigger_up('display_updated_question', {
                    newQuestionRenderedTemplate: renderedQuestion,
                    editedQuestion: this.editedQuestion,
                    questionFormWidget: this,
                });
            } else {
                this.el.querySelector('.o_wslides_js_quiz_validation_error').classList.add('d-none');
                this.trigger_up('display_created_question', {
                    newQuestionRenderedTemplate: renderedQuestion,
                    questionFormWidget: this
                });
            }
        } else {
            const errorEl = this.el.querySelector('.o_wslides_js_quiz_validation_error');
            errorEl.classList.remove('d-none');
            const errorText = errorEl.querySelector('.o_wslides_js_quiz_validation_error_text');
            errorText.textContent = _t('Please fill in the question');
            this.el.querySelector('.o_wslides_quiz_question input').focus();
        }
    },

    /**
     * Check if the Question has been filled up
     * @param form
     * @returns {boolean}
     * @private
     */
    _isValidForm: function(form) {
        return form.querySelector('.o_wslides_quiz_question input[type=text]').value.trim() !== "";
    },

    /**
     * Serialize the form into a JSON object to send it
     * to the server through a RPC call.
     * @param form
     * @returns {{id: *, sequence: *, question: *, slide_id: *, answer_ids: Array}}
     * @private
     */
    _serializeForm: function (form) {
        const answers = [];
        let sequence = 1;
        [...form.querySelectorAll('.o_wslides_js_quiz_answer')].forEach(() => {
            const value = this.el.querySelector('.o_wslides_js_quiz_answer_value').value;
            if (value.trim() !== "") {
                const answer = {
                    'sequence': sequence++,
                    'text_value': value,
                    'is_correct': this.el.querySelector('input[type=radio]').checked === true,
                    'comment': this.el.querySelector('.o_wslides_js_quiz_answer_comment > input[type=text]').value.trim()
                };
                answers.push(answer);
            }
        });
        return {
            'existing_question_id': this.el.dataset.id,
            'sequence': this.sequence,
            'question': form.querySelector('.o_wslides_quiz_question input[type=text]').value,
            'slide_id': this.slideId,
            'answer_ids': answers
        };
    },

});

export default QuestionFormWidget;
