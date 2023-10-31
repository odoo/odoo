/** @odoo-module **/

import publicWidget from 'web.public.widget';
import core from 'web.core';

var QWeb = core.qweb;
var _t = core._t;

/**
 * This Widget is responsible of displaying the question inputs when adding a new question or when updating an
 * existing one. When validating the question it makes an RPC call to the server and trigger an event for
 * displaying the question by the Quiz widget.
 */
var QuestionFormWidget = publicWidget.Widget.extend({
    template: 'slide.quiz.question.input',
    xmlDependencies: ['/website_slides/static/src/xml/slide_quiz_create.xml'],
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
        this.$editedQuestion = options.editedQuestion;
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
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$('.o_wslides_quiz_question input').focus();
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
        var input = event.currentTarget;
        var commentIcon = $(input).closest('.o_wslides_js_quiz_answer').find('.o_wslides_js_quiz_comment_answer');
        if (input.value.trim() !== '') {
            commentIcon.addClass('text-primary');
            commentIcon.removeClass('text-muted');
        } else {
            commentIcon.addClass('text-muted');
            commentIcon.removeClass('text-primary');
        }
    },

    /**
     * Toggle the input for commenting the answer line which will be
     * seen by the frontend user when submitting the quiz.
     * @param ev
     * @private
     */
    _toggleAnswerLineComment: function (ev) {
        var commentLine = $(ev.currentTarget).closest('.o_wslides_js_quiz_answer').find('.o_wslides_js_quiz_answer_comment').toggleClass('d-none');
        commentLine.find('input[type=text]').focus();
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
        $(ev.currentTarget).closest('.o_wslides_js_quiz_answer').after(QWeb.render('slide.quiz.answer.line'));
    },

    /**
     * Removes an answer line. Can't remove the last answer line.
     * @param ev
     * @private
     */
    _removeAnswerLine: function (ev) {
        if (this.$('.o_wslides_js_quiz_answer').length > 1) {
            $(ev.currentTarget).closest('.o_wslides_js_quiz_answer').remove();
        }
    },

    /**
     *
     * @param ev
     * @private
     */
    _removeAnswerLineComment: function (ev) {
        var commentLine = $(ev.currentTarget).closest('.o_wslides_js_quiz_answer_comment').addClass('d-none');
        commentLine.find('input[type=text]').val('').change();
    },

    /**
     * Handler when user click on 'Save' or 'Update' buttons.
     * @param ev
     * @private
     */
    _validateQuestion: function (ev) {
        this._createOrUpdateQuestion({
            update: $(ev.currentTarget).hasClass('o_wslides_js_quiz_update'),
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
    _createOrUpdateQuestion: function (options) {
        var self = this;
        var $form = this.$('form');
        if (this._isValidForm($form)) {
            var values = this._serializeForm($form);
            this._rpc({
                route: '/slides/slide/quiz/question_add_or_update',
                params: values
            }).then(function (renderedQuestion) {
                if (options.update) {
                    self.trigger_up('display_updated_question', {
                        newQuestionRenderedTemplate: renderedQuestion,
                        $editedQuestion: self.$editedQuestion,
                        questionFormWidget: self,
                    });
                } else {
                    self.trigger_up('display_created_question', {
                        newQuestionRenderedTemplate: renderedQuestion,
                        questionFormWidget: self
                    });
                }
            });
        } else {
            this.displayNotification({
                type: 'warning',
                message: _t('Please fill in the question'),
                sticky: true
            });
            this.$('.o_wslides_quiz_question input').focus();
        }
    },

    /**
     * Check if the Question has been filled up
     * @param $form
     * @returns {boolean}
     * @private
     */
    _isValidForm: function($form) {
        return $form.find('.o_wslides_quiz_question input[type=text]').val().trim() !== "";
    },

    /**
     * Serialize the form into a JSON object to send it
     * to the server through a RPC call.
     * @param $form
     * @returns {{id: *, sequence: *, question: *, slide_id: *, answer_ids: Array}}
     * @private
     */
    _serializeForm: function ($form) {
        var answers = [];
        var sequence = 1;
        $form.find('.o_wslides_js_quiz_answer').each(function () {
            var value = $(this).find('.o_wslides_js_quiz_answer_value').val();
            if (value.trim() !== "") {
                var answer = {
                    'sequence': sequence++,
                    'text_value': value,
                    'is_correct': $(this).find('input[type=radio]').prop('checked') === true,
                    'comment': $(this).find('.o_wslides_js_quiz_answer_comment > input[type=text]').val().trim()
                };
                answers.push(answer);
            }
        });
        return {
            'existing_question_id': this.$el.data('id'),
            'sequence': this.sequence,
            'question': $form.find('.o_wslides_quiz_question input[type=text]').val(),
            'slide_id': this.slideId,
            'answer_ids': answers
        };
    },

});

export default QuestionFormWidget;
