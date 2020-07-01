odoo.define('gamification_quiz.quiz', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var session = require('web.session');

    var QuestionFormWidget = require('gamification_quiz.quiz.question.form');
    var QuizFinishModal = require('gamification_quiz.quiz.finish');

    var QWeb = core.qweb;
    var _t = core._t;

    /**
     * This widget is responsible of displaying quiz questions and propositions. Submitting the quiz will fetch the
     * correction and decorate the answers according to the result. Error message or modal can be displayed.
     *
     * This widget can be attached to DOM rendered server-side by `gamification_quiz.` or
     * used client side (Fullscreen).
     *
     * Triggered events are :
     * - quiz_completed: when the quiz is passed and completed by the user. Event data contains current container data.
     */
    var Quiz = publicWidget.Widget.extend({
        template: 'quiz.main',
        xmlDependencies: ['/gamification_quiz/static/src/xml/quiz_templates.xml'],
        events: {
            "click .o_quiz_quiz_answer": '_onAnswerClick',
            "click .o_quiz_js_quiz_submit": '_submitQuiz',
            "click .o_quiz_quiz_modal_btn": '_onClickNext',
            "click .o_quiz_js_quiz_reset": '_onClickReset',
            'click .o_quiz_js_quiz_add': '_onCreateQuizClick',
            'click .o_quiz_js_quiz_edit_question': '_onEditQuestionClick',
            'click .o_quiz_js_quiz_delete_question': '_onDeleteQuestionClick',
        },

        custom_events: {
            display_created_question: '_displayCreatedQuestion',
            display_updated_question: '_displayUpdatedQuestion',
            reset_display: '_resetDisplay',
            delete_question: '_deleteQuestion',
        },

        /**
        * @override
        * @param {Object} parent
        * @param {Object} data holding all the container information
        * @param {Object} quiz_data : optional quiz data to display. If not given, will be fetched. (questions and answers).
        */
        init: function (parent, data, quizData) {
            this._super.apply(this, arguments);
            this.object = _.defaults(data, {
                id: 0,
                name: '',
                model: '',
                completed: false,
                isMember: false,
                progressBar: false
            });
            this.quiz = quizData || false;
            console.log(this.quiz);
            if (this.quiz) {
                this.quiz.questionsCount = quizData.questions.length;
            }
            this.isMember = data.isMember || false;
            this.publicUser = session.is_website_user;
            this.userId = session.user_id;
            this.redirectURL = encodeURIComponent(document.URL);
        },

        /**
         * @override
         */
        willStart: function () {
            var defs = [this._super.apply(this, arguments)];
            if (!this.quiz) {
                defs.push(this._fetchQuiz());
            }
            return Promise.all(defs);
        },

        /**
         * Overridden to add custom rendering behavior upon start of the widget.
         *
         * If the user has answered the quiz before having joined the course, we check
         * his answers (saved into his session) here as well.
         *
         * @override
         */
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function ()  {
                self._renderValidationInfo();
                self._bindSortable();
                self._checkLocationHref();
                if (!self.isMember) {
                    // self._renderJoinWidget();
                } else if (self.object.sessionAnswers) {
                    self._applySessionAnswers();
                    self._submitQuiz();
                }
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _alertShow: function (alertCode) {
            var message = _t('There was an error validating this quiz.');
            if (alertCode === 'quiz_incomplete') {
                message = _t('All questions must be answered !');
            } else if (alertCode === 'quiz_done') {
                message = _t('This quiz is already done. Retaking it is not possible.');
            } else if (alertCode === 'public_user') {
                message = _t('You must be logged to submit the quiz.');
            }

            this.displayNotification({
                type: 'warning',
                title: _t('Quiz validation error'),
                message: message,
                sticky: true
            });
        },

        /**
         * Allows to reorder the questions
         * @private
         */
        _bindSortable: function () {
            this.$el.sortable({
                handle: '.o_quiz_js_quiz_sequence_handler',
                items: '.o_quiz_js_quiz_question',
                stop: this._reorderQuestions.bind(this),
                placeholder: 'o_quiz_js_quiz_sequence_highlight position-relative my-3'
            });
        },

        /**
         * Get all the questions ID from the displayed Quiz
         * @returns {Array}
         * @private
         */
        _getQuestionsIds: function () {
            return this.$('.o_quiz_js_quiz_question').map(function () {
                return $(this).data('question-id');
            }).get();
        },

        /**
         * Modify visually the sequence of all the questions after
         * calling the _reorderQuestions RPC call.
         * @private
         */
        _modifyQuestionsSequence: function () {
            this.$('.o_quiz_js_quiz_question').each(function (index, question) {
                $(question).find('span.o_quiz_quiz_question_sequence').text(index + 1);
            });
        },

        /**
         * RPC call to resequence all the questions. It is called
         * after modifying the sequence of a question and also after
         * deleting a question.
         * @private
         */
        _reorderQuestions: function () {
            this._rpc({
                route: '/web/dataset/resequence',
                params: {
                    model: "quiz.question",
                    ids: this._getQuestionsIds()
                }
            }).then(this._modifyQuestionsSequence.bind(this))
        },
        /*
         * @private
         * Fetch the quiz
         */
        _fetchQuiz: function () {
            var self = this;
            return self._rpc({
                route:'/gamification_quiz/quiz/get',
                params: {
                    'model': self.object.model,
                    'object_id': self.object.id,
                }
            }).then(function (quiz_data) {
                self.quiz = {
                    questions: quiz_data.quiz_questions || [],
                    questionsCount: quiz_data.quiz_questions.length,
                    quizAttemptsCount: quiz_data.quiz_attempts_count || 0,
                    quizKarmaGain: quiz_data.quiz_karma_gain || 0,
                    quizKarmaWon: quiz_data.quiz_karma_won || 0,
                };
            });
        },

        /**
         * Hide the edit and delete button and also the handler
         * to resequence the question
         * @private
         */
        _hideEditOptions: function () {
            this.$('.o_quiz_js_lesson_quiz_question .o_quiz_js_quiz_edit_del,' +
                   ' .o_quiz_js_lesson_quiz_question .o_quiz_js_quiz_sequence_handler').addClass('d-none');
        },

        /**
         * @private
         * Decorate the answers according to state
         */
        _disableAnswers: function () {
            var self = this;
            this.$('.o_quiz_js_lesson_quiz_question').addClass('completed-disabled');
            this.$('input[type=radio]').each(function () {
                $(this).prop('disabled', self.object.completed);
            });
        },

        /**
         * Decorate the answer inputs according to the correction and adds the answer comment if
         * any.
         *
         * @private
         */
        _renderAnswersHighlightingAndComments: function () {
            var self = this;
            this.$('.o_quiz_js_quiz_question').each(function () {
                var $question = $(this);
                var questionId = $question.data('questionId');
                var isCorrect = self.quiz.answers[questionId].is_correct;
                $question.find('a.o_quiz_quiz_answer').each(function () {
                    var $answer = $(this);
                    $answer.find('i.fa').addClass('d-none');
                    if ($answer.find('input[type=radio]')[0].checked) {
                        if (isCorrect) {
                            $answer.removeClass('list-group-item-danger').addClass('list-group-item-success');
                            $answer.find('i.fa-check-circle').removeClass('d-none');
                        } else {
                            $answer.removeClass('list-group-item-success').addClass('list-group-item-danger');
                            $answer.find('i.fa-times-circle').removeClass('d-none');
                            $answer.find('label input').prop('checked', false);
                        }
                    } else {
                        $answer.removeClass('list-group-item-danger list-group-item-success');
                        $answer.find('i.fa-circle').removeClass('d-none');
                    }
                });
                var comment = self.quiz.answers[questionId].comment;
                if (comment) {
                    $question.find('.o_quiz_quiz_answer_info').removeClass('d-none');
                    $question.find('.o_quiz_quiz_answer_comment').text(comment);
                }
            });
        },

        /**
         * Will check if we have answers coming from the session and re-apply them.
         */
        _applySessionAnswers: function () {
            if (!this.object.sessionAnswers || this.object.sessionAnswers.length === 0) {
                return;
            }

            var self = this;
            this.$('.o_quiz_js_quiz_question').each(function () {
                var $question = $(this);
                $question.find('a.o_quiz_quiz_answer').each(function () {
                    var $answer = $(this);
                    if (!$answer.find('input[type=radio]')[0].checked &&
                        _.contains(self.object.sessionAnswers, $answer.data('answerId'))) {
                        $answer.find('input[type=radio]').prop('checked', true);
                    }
                });
            });

            // reset answers coming from the session
            this.object.sessionAnswers = false;
        },

        /*
         * @private
         * Update validation box (karma, buttons) according to widget state
         */
        _renderValidationInfo: function () {
            var $validationElem = this.$('.o_quiz_js_quiz_validation');
            $validationElem.html(
                QWeb.render('quiz.validation', {'widget': this})
            );
        },

        /**
         * Get the quiz answers filled in by the User
         *
         * @private
         */
        _getQuizAnswers: function () {
            return this.$('input[type=radio]:checked').map(function (index, element) {
                return parseInt($(element).val());
            }).get();
        },

        /**
         * Submit a quiz and get the correction. It will display messages
         * according to quiz result.
         *
         * @private
         */
        _submitQuiz: function () {
            var self = this;

            return this._rpc({
                route: '/gamification_quiz/quiz/submit',
                params: {
                    model: self.object.model,
                    object_id: self.object.id,
                    answer_ids: this._getQuizAnswers(),
                }
            }).then(function (data) {
                if (data.error) {
                    self._alertShow(data.error);
                } else {
                    self.quiz = _.extend(self.quiz, data);
                    self.quiz.quizPointsGained = data.points_gained;
                    if (data.quiz_completed) {
                        self._disableAnswers();
                        new QuizFinishModal(self, {
                            quiz: self.quiz,
                            hasNext: self.object.hasNext,
                            userId: self.userId,
                            progressBar: self.progressBar
                        }).open();
                        self.object.completed = data.quiz_completed;
                        // self.trigger_up('object_completed', {object: self.object, completion: data.channel_completion});
                    }
                    self._hideEditOptions();
                    self._renderAnswersHighlightingAndComments();
                    self._renderValidationInfo();
                }
            });
        },

        /**
         * Get all the question information after clicking on
         * the edit button
         * @param $elem
         * @returns {{id: *, sequence: number, text: *, answers: Array}}
         * @private
         */
        _getQuestionDetails: function ($elem) {
            var answers = [];
            $elem.find('.o_quiz_quiz_answer').each(function () {
                answers.push({
                    'id': $(this).data('answerId'),
                    'text_value': $(this).data('text'),
                    'is_correct': $(this).data('isCorrect'),
                    'comment': $(this).data('comment')
                });
            });
            return {
                'id': $elem.data('questionId'),
                'sequence': parseInt($elem.find('.o_quiz_quiz_question_sequence').text()),
                'text': $elem.data('title'),
                'answers': answers,
            };
        },

        /**
         * If the object has been called with the Add Quiz button on the object list
         * it goes straight to the 'Add Quiz' button and clicks on it.
         * @private
         */
        _checkLocationHref: function () {
            if (window.location.href.includes('quiz_quick_create')) {
                this._onCreateQuizClick();
            }
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * When clicking on an answer, this one should be marked as "checked".
         *
         * @private
         * @param OdooEvent ev
         */
        _onAnswerClick: function (ev) {
            ev.preventDefault();
            if (!this.object.completed) {
                $(ev.currentTarget).find('input[type=radio]').prop('checked', true);
            }
        },

        /**
         * Triggering a event to switch to next object
         *
         * @private
         * @param OdooEvent ev
         */
        _onClickNext: function (ev) {
            if (this.object.hasNext) {
                this.trigger_up('object_go_next');
            }
        },

        /**
         * Resets the completion of the object so the user can take
         * the quiz again
         *
         * @private
         */
        _onClickReset: function () {
            this._rpc({
                route: '/gamification_quiz/quiz/reset',
                params: {
                    model: this.object.model,
                    object_id: this.object.id
                }
            }).then(function () {
                window.location.reload();
            });
        },
        /**
         * Saves the answers from the user and redirect the user to the
         * specified url
         *
         * @private
         */
        _saveQuizAnswersToSession: function () {
            var quizAnswers = this._getQuizAnswers();
            if (quizAnswers.length === this.quiz.questions.length) {
                return this._rpc({
                    route: '/gamification_quiz/quiz/save_to_session',
                    params: {
                        'model': this.model,
                        'quiz_answers': {'object_id': this.object.id, 'object_answers': quizAnswers},
                    }
                });
            } else {
                this._alertShow('quiz_incomplete');
                return Promise.reject('The quiz is incomplete');
            }
        },
        /**
        * After joining the course, we immediately submit the quiz and get the correction.
        * This allows a smooth onboarding when the user is logged in and the course is public.
        *
        * @private
        */
       _afterJoin: function () {
            this.isMember = true;
            this._renderValidationInfo();
            this._applySessionAnswers();
            this._submitQuiz();
       },

        /**
         * When clicking on 'Add a Question' or 'Add Quiz' it
         * initialize a new QuestionFormWidget to input the new
         * question.
         * @private
         */
        _onCreateQuizClick: function () {
            var $elem = this.$('.o_quiz_js_quiz_new_question');
            this.$('.o_quiz_js_quiz_add').addClass('d-none');
            new QuestionFormWidget(this, {
                objectId: this.object.id,
                model: this.model,
                sequence: this.quiz.questionsCount + 1
            }).appendTo($elem);
        },

        /**
         * When clicking on the edit button of a question it
         * initialize a new QuestionFormWidget with the existing
         * question as inputs.
         * @param ev
         * @private
         */
        _onEditQuestionClick: function (ev) {
            var $editedQuestion = $(ev.currentTarget).closest('.o_quiz_js_quiz_quiz_question');
            var question = this._getQuestionDetails($editedQuestion);
            new QuestionFormWidget(this, {
                editedQuestion: $editedQuestion,
                question: question,
                model: this.model,
                objectId: this.object.id,
                sequence: question.sequence,
                update: true
            }).insertAfter($editedQuestion);
            $editedQuestion.hide();
        },

        /**
         * When clicking on the delete button of a question it
         * toggles a modal to confirm the deletion
         * @param ev
         * @private
         */
        _onDeleteQuestionClick: function (ev) {
            var question = $(ev.currentTarget).closest('.o_quiz_js_quiz_question');
            new ConfirmationDialog(this, {
                questionId: question.data('questionId'),
                questionTitle: question.data('title')
            }).open();
        },

        /**
         * Displays the created Question at the correct place (after the last question or
         * at the first place if there is no questions yet) It also displays the 'Add Question'
         * button or open a new QuestionFormWidget if the user wants to immediately add another one.
         *
         * @param event
         * @private
         */
        _displayCreatedQuestion: function (event) {
            var $lastQuestion = this.$('.o_quiz_js_quiz_question:last');
            if ($lastQuestion.length !== 0) {
                $lastQuestion.after(event.data.newQuestionRenderedTemplate);
            } else {
                this.$el.prepend(event.data.newQuestionRenderedTemplate);
            }
            this.quiz.questionsCount++;
            event.data.questionFormWidget.destroy();
            if (event.data.save_and_new) {
                this._onCreateQuizClick();
            } else {
                this.$('.o_quiz_js_quiz_add_question').removeClass('d-none');
            }
        },

        /**
         * Replace the edited question by the new question and destroy
         * the QuestionFormWidget.
         * @param event
         * @private
         */
        _displayUpdatedQuestion: function (event) {
            var questionFormWidget = event.data.questionFormWidget;
            event.data.$editedQuestion.replaceWith(event.data.newQuestionRenderedTemplate);
            questionFormWidget.destroy();
        },

        /**
         * If the user cancels the creation or update of a Question it resets the display
         * of the updated Question or it displays back the buttons.
         *
         * @param event
         * @private
         */
        _resetDisplay: function (event) {
            var questionFormWidget = event.data.questionFormWidget;
            if (questionFormWidget.update) {
                questionFormWidget.$editedQuestion.show();
            } else {
                if (this.quiz.questionsCount > 0) {
                    this.$('.o_quiz_js_quiz_add_question').removeClass('d-none');
                } else {
                    this.$('.o_quiz_js_quiz_add_quiz').removeClass('d-none');
                }
            }
            questionFormWidget.destroy();
        },

        /**
         * After deletion of a Question the display is refreshed with the removal of the Question
         * the reordering of all the remaining Questions and the change of the new Question sequence
         * if the QuestionFormWidget is initialized.
         *
         * @param event
         * @private
         */
        _deleteQuestion: function (event) {
            var questionId = event.data.questionId;
            this.$('.o_quiz_js_lesson_quiz_question[data-question-id=' + questionId + ']').remove();
            this.quiz.questionsCount--;
            this._reorderQuestions();
            var $newQuestionSequence = this.$('.o_quiz_js_lesson_quiz_new_question .o_quiz_quiz_question_sequence');
            $newQuestionSequence.text(parseInt($newQuestionSequence.text()) - 1);
            if (this.quiz.questionsCount === 0 && !this.$('.o_wsildes_quiz_question_input').length) {
                this.$('.o_quiz_js_quiz_add_quiz').removeClass('d-none');
                this.$('.o_quiz_js_quiz_add_question').addClass('d-none');
                this.$('.o_quiz_js_quiz_validation').addClass('d-none');
            }
        },
    });

    /**
     * Dialog box shown when clicking the deletion button on a Question.
     * When confirming it sends a RPC request to delete the Question.
     */
    var ConfirmationDialog = Dialog.extend({
        template: 'quiz.confirm.deletion',
        xmlDependencies: Dialog.prototype.xmlDependencies.concat(
            ['/gamification_quiz/static/src/xml/quiz_create.xml']
        ),

        /**
         * @override
         * @param parent
         * @param options
         */
        init: function (parent, options) {
            options = _.defaults(options || {}, {
                title: _t('Delete Question'),
                buttons: [
                    { text: _t('Yes'), classes: 'btn-primary', click: this._onConfirmClick },
                    { text: _t('No'), close: true}
                ],
                size: 'medium'
            });
            this.questionId = options.questionId;
            this.questionTitle = options.questionTitle;
            this._super.apply(this, arguments);
        },

        /**
         * Handler when the user confirm the deletion by clicking on 'Yes'
         * it sends a RPC request to the server and triggers an event to
         * visually delete the question.
         * @private
         */
        _onConfirmClick: function () {
            var self = this;
            this._rpc({
                model: 'quiz.question',
                method: 'unlink',
                args: [this.questionId],
            }).then(function () {
                self.trigger_up('delete_question', { questionId: self.questionId });
                self.close();
            });
        }
    });

    publicWidget.registry.Quiz = publicWidget.Widget.extend({
        selector: '.o_quiz_main',

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @override
         * @param {Object} parent
         */
        start: function () {
            var self = this;
            this.quizWidgets = [];
            var defs = [this._super.apply(this, arguments)];
            this.$('.o_quiz_js_quiz').each(function () {
                var data = $(this).data();
                data.quizData = {
                    questions: self._extractQuestionsAndAnswers(),
                    sessionAnswers: data.sessionAnswers || [],
                    quizKarmaMax: data.quizKarmaMax,
                    quizKarmaWon: data.quizKarmaWon,
                    quizKarmaGain: data.quizKarmaGain,
                    quizPointsGained: data.quizPointsGained,
                    quizAttemptsCount: data.quizAttemptsCount,
                };
                defs.push(new Quiz(self, data, data.quizData).attachTo($(this)));
            });
            return Promise.all(defs);
        },

        //----------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * Extract data from exiting DOM rendered server-side, to have the list of questions with their
         * relative answers.
         * This method should return the same format as /gamification_quiz/quiz/get controller.
         *
         * @return {Array<Object>} list of questions with answers
         */
        _extractQuestionsAndAnswers: function () {
            var questions = [];
            this.$('.o_quiz_js_quiz_question').each(function () {
                var $question = $(this);
                var answers = [];
                $question.find('.o_quiz_quiz_answer').each(function () {
                    var $answer = $(this);
                    answers.push({
                        id: $answer.data('answerId'),
                        text: $answer.data('text'),
                    });
                });
                questions.push({
                    id: $question.data('questionId'),
                    title: $question.data('title'),
                    answer_ids: answers,
                });
            });
            return questions;
        },
    });

    return {
        Quiz: Quiz,
        ConfirmationDialog: ConfirmationDialog,
        QuizLauncher: publicWidget.registry.QuizLauncher
    };
});
