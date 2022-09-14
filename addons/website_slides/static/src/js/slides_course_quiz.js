/** @odoo-module **/

    import publicWidget from 'web.public.widget';
    import Dialog from 'web.Dialog';
    import  { qweb as QWeb, _t } from 'web.core';
    import session from 'web.session';
    import { Markup } from 'web.utils';
    import CourseJoin from '@website_slides/js/slides_course_join';
    import QuestionFormWidget from '@website_slides/js/slides_course_quiz_question_form';
    import SlideQuizFinishModal from '@website_slides/js/slides_course_quiz_finish';
    import { SlideCoursePage } from '@website_slides/js/slides_course_page';

    import SlideEnroll from '@website_slides/js/slides_course_enroll_email';

    const CourseJoinWidget = CourseJoin.courseJoinWidget;
    const SlideEnrollDialog = SlideEnroll.slideEnrollDialog;

    /**
     * This widget is responsible of displaying quiz questions and propositions. Submitting the quiz will fetch the
     * correction and decorate the answers according to the result. Error message or modal can be displayed.
     *
     * This widget can be attached to DOM rendered server-side by `website_slides.slide_category_quiz` or
     * used client side (Fullscreen).
     *
     * Triggered events are :
     * - slide_go_next: need to go to the next slide, when quiz is done. Event data contains the current slide id.
     * - quiz_completed: when the quiz is passed and completed by the user. Event data contains current slide data.
     */
    var Quiz = publicWidget.Widget.extend({
        template: 'slide.slide.quiz',
        events: {
            "click .o_wslides_quiz_answer": '_onAnswerClick',
            "click .o_wslides_js_lesson_quiz_submit": '_submitQuiz',
            "click .o_wslides_quiz_modal_btn": '_onClickNext',
            "click .o_wslides_quiz_continue": '_onClickNext',
            "click .o_wslides_js_lesson_quiz_reset": '_onClickReset',
            'click .o_wslides_js_quiz_add': '_onCreateQuizClick',
            'click .o_wslides_js_quiz_edit_question': '_onEditQuestionClick',
            'click .o_wslides_js_quiz_delete_question': '_onDeleteQuestionClick',
            'click .o_wslides_js_channel_enroll': '_onSendRequestToResponsibleClick',
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
        * @param {Object} slide_data holding all the classic slide information
        * @param {Object} quiz_data : optional quiz data to display. If not given, will be fetched. (questions and answers).
        */
        init: function (parent, slide_data, channel_data, quiz_data) {
            this._super.apply(this, arguments);
            this.slide = _.defaults(slide_data, {
                id: 0,
                name: '',
                hasNext: false,
                completed: false,
                isMember: false,
            });
            this.quiz = quiz_data || false;
            if (this.quiz) {
                this.quiz.questionsCount = quiz_data.questions.length;
            }
            this.isMember = slide_data.isMember || false;
            this.publicUser = session.is_website_user;
            this.userId = session.user_id;
            this.redirectURL = encodeURIComponent(document.URL);
            this.channel = channel_data;
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
         * their answers (saved into their session) here as well.
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
                    self._renderJoinWidget();
                } else if (self.slide.sessionAnswers) {
                    self._applySessionAnswers();
                    self._submitQuiz();
                }
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _showErrorMessage: function (errorCode) {
            var message = _t('There was an error validating this quiz.');
            if (errorCode === 'slide_quiz_incomplete') {
                message = _t('All questions must be answered !');
            } else if (errorCode === 'slide_quiz_done') {
                message = _t('This quiz is already done. Retaking it is not possible.');
            } else if (errorCode === 'public_user') {
                message = _t('You must be logged to submit the quiz.');
            }

            this.$('.o_wslides_js_quiz_submit_error')
                .removeClass('d-none')
                .find('.o_wslides_js_quiz_submit_error_text')
                .text(message);
        },

        _hideErrorMessage: function () {
            this.$('.o_wslides_js_quiz_submit_error')
                .addClass('d-none');
        },

        /**
         * Allows to reorder the questions
         * @private
         */
        _bindSortable: function () {
            this.$el.sortable({
                handle: '.o_wslides_js_quiz_sequence_handler',
                items: '.o_wslides_js_lesson_quiz_question',
                stop: this._reorderQuestions.bind(this),
                placeholder: 'o_wslides_js_quiz_sequence_highlight position-relative my-3'
            });
        },

        /**
         * Get all the questions ID from the displayed Quiz
         * @returns {Array}
         * @private
         */
        _getQuestionsIds: function () {
            return this.$('.o_wslides_js_lesson_quiz_question').map(function () {
                return $(this).data('question-id');
            }).get();
        },

        /**
         * Modify visually the sequence of all the questions after
         * calling the _reorderQuestions RPC call.
         * @private
         */
        _modifyQuestionsSequence: function () {
            this.$('.o_wslides_js_lesson_quiz_question').each(function (index, question) {
                $(question).find('span.o_wslides_quiz_question_sequence').text(index + 1);
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
                    model: "slide.question",
                    ids: this._getQuestionsIds()
                }
            }).then(this._modifyQuestionsSequence.bind(this))
        },
        /*
         * @private
         * Fetch the quiz for a particular slide
         */
        _fetchQuiz: function () {
            var self = this;
            return self._rpc({
                route:'/slides/slide/quiz/get',
                params: {
                    'slide_id': self.slide.id,
                }
            }).then(function (quiz_data) {
                self.slide.sessionAnswers = quiz_data.session_answers;
                self.quiz = {
                    questions: quiz_data.slide_questions || [],
                    questionsCount: quiz_data.slide_questions.length,
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
            this.$('.o_wslides_js_lesson_quiz_question .o_wslides_js_quiz_edit_del,' +
                   ' .o_wslides_js_lesson_quiz_question .o_wslides_js_quiz_sequence_handler').addClass('d-none');
        },

        /**
         * @private
         * Decorate the answers according to state
         */
        _disableAnswers: function () {
            var self = this;
            this.$('.o_wslides_js_lesson_quiz_question').addClass('completed-disabled');
            this.$('input[type=radio]').each(function () {
                $(this).prop('disabled', self.slide.completed);
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
            this.$('.o_wslides_js_lesson_quiz_question').each(function () {
                var $question = $(this);
                var questionId = $question.data('questionId');
                var isCorrect = self.quiz.answers[questionId].is_correct;
                $question.find('a.o_wslides_quiz_answer').each(function () {
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
                    $question.find('.o_wslides_quiz_answer_info').removeClass('d-none');
                    $question.find('.o_wslides_quiz_answer_comment').text(comment);
                }
            });
        },

        /**
         * Will check if we have answers coming from the session and re-apply them.
         */
        _applySessionAnswers: function () {
            if (!this.slide.sessionAnswers || this.slide.sessionAnswers.length === 0) {
                return;
            }

            var self = this;
            this.$('.o_wslides_js_lesson_quiz_question').each(function () {
                var $question = $(this);
                $question.find('a.o_wslides_quiz_answer').each(function () {
                    var $answer = $(this);
                    if (!$answer.find('input[type=radio]')[0].checked &&
                        _.contains(self.slide.sessionAnswers, $answer.data('answerId'))) {
                        $answer.find('input[type=radio]').prop('checked', true);
                    }
                });
            });

            // reset answers coming from the session
            this.slide.sessionAnswers = false;
        },

        /*
         * @private
         * Update validation box (karma, buttons) according to widget state
         */
        _renderValidationInfo: function () {
            var $validationElem = this.$('.o_wslides_js_lesson_quiz_validation');
            $validationElem.html(
                QWeb.render('slide.slide.quiz.validation', {'widget': this})
            );
        },

        /**
         * Renders the button to join a course.
         * If the user is logged in, the course is public, and the user has previously tried to
         * submit answers, we automatically attempt to join the course.
         *
         * @private
         */
        _renderJoinWidget: function () {
            var $widgetLocation = this.$(".o_wslides_join_course_widget");
            if ($widgetLocation.length !== 0) {
                var courseJoinWidget = new CourseJoinWidget(this, {
                    isQuiz: true,
                    channel: this.channel,
                    isMember: this.isMember,
                    publicUser: this.publicUser,
                    beforeJoin: this._saveQuizAnswersToSession.bind(this),
                    afterJoin: this._afterJoin.bind(this),
                    joinMessage: _t('Join & Submit'),
                });

                courseJoinWidget.appendTo($widgetLocation);
                if (!this.publicUser && courseJoinWidget.channel.channelEnroll === 'public' && this.slide.sessionAnswers) {
                    courseJoinWidget.joinChannel(this.channel.channelId);
                }
            }
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
         async _submitQuiz() {
            const data = await this._rpc({
                route: '/slides/slide/quiz/submit',
                params: {
                    slide_id: this.slide.id,
                    answer_ids: this._getQuizAnswers(),
                }
            });
            if (data.error) {
                this._showErrorMessage(data.error);
                return;
            } else {
                this._hideErrorMessage();
            }
            Object.assign(this.quiz, data);
            const {rankProgress, completed, channel_completion: completion} = this.quiz;
            // two of the rankProgress properties are HTML messages, mark if set
            if ('description' in rankProgress) {
                rankProgress['description'] = Markup(rankProgress['description'] || '');
                rankProgress['previous_rank']['motivational'] =
                    Markup(rankProgress['previous_rank']['motivational'] || '');
            }
            if (completed) {
                this._disableAnswers();
                new SlideQuizFinishModal(this, {
                    quiz: this.quiz,
                    hasNext: this.slide.hasNext,
                    userId: this.userId
                }).open();
                this.slide.completed = true;
                this.trigger_up('slide_completed', {
                    slideId: this.slide.id,
                    channelCompletion: completion,
                    completed: true,
                });
            }
            this._hideEditOptions();
            this._renderAnswersHighlightingAndComments();
            this._renderValidationInfo();
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
            $elem.find('.o_wslides_quiz_answer').each(function () {
                answers.push({
                    'id': $(this).data('answerId'),
                    'text_value': $(this).data('text'),
                    'is_correct': $(this).data('isCorrect'),
                    'comment': $(this).data('comment')
                });
            });
            return {
                'id': $elem.data('questionId'),
                'sequence': parseInt($elem.find('.o_wslides_quiz_question_sequence').text()),
                'text': $elem.data('title'),
                'answers': answers,
            };
        },

        /**
         * If the slides has been called with the Add Quiz button on the slide list
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
            if (!this.slide.completed) {
                $(ev.currentTarget).find('input[type=radio]').prop('checked', true);
            }
        },

        /**
         * Triggering a event to switch to next slide
         *
         * @private
         * @param OdooEvent ev
         */
        _onClickNext: function (ev) {
            if (this.slide.hasNext) {
                this.trigger_up('slide_go_next');
            }
        },

        /**
         * Resets the completion of the slide so the user can take
         * the quiz again
         *
         * @private
         */
        _onClickReset: function () {
            this._rpc({
                route: '/slides/slide/quiz/reset',
                params: {
                    slide_id: this.slide.id
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
            this._hideErrorMessage();

            return this._rpc({
                route: '/slides/slide/quiz/save_to_session',
                params: {
                    'quiz_answers': {'slide_id': this.slide.id, 'slide_answers': this._getQuizAnswers()},
                }
            });
        },
        /**
        * After joining the course, we save the questions in the session
        * and reload the page to update the view.
        *
        * @private
        */
       _afterJoin: function () {
            this._saveQuizAnswersToSession().then(() => {
                window.location.reload();
            });
       },

        /**
         * When clicking on 'Add a Question' or 'Add Quiz' it
         * initialize a new QuestionFormWidget to input the new
         * question.
         * @private
         */
        _onCreateQuizClick: function () {
            var $elem = this.$('.o_wslides_js_lesson_quiz_new_question');
            this.$('.o_wslides_js_quiz_add').addClass('d-none');
            new QuestionFormWidget(this, {
                slideId: this.slide.id,
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
            var $editedQuestion = $(ev.currentTarget).closest('.o_wslides_js_lesson_quiz_question');
            var question = this._getQuestionDetails($editedQuestion);
            new QuestionFormWidget(this, {
                editedQuestion: $editedQuestion,
                question: question,
                slideId: this.slide.id,
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
            var question = $(ev.currentTarget).closest('.o_wslides_js_lesson_quiz_question');
            new ConfirmationDialog(this, {
                questionId: question.data('questionId'),
                questionTitle: question.data('title')
            }).open();
        },

        /**
         * Handler for the contact responsible link below a Quiz
         * @param ev
         * @private
         */
        _onSendRequestToResponsibleClick: function(ev) {
            ev.preventDefault();
            var channelId = $(ev.currentTarget).data('channelId');
            new SlideEnrollDialog(this, {
                channelId: channelId,
                $element: $(ev.currentTarget).closest('.alert.alert-info')
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
            var $lastQuestion = this.$('.o_wslides_js_lesson_quiz_question:last');
            if ($lastQuestion.length !== 0) {
                $lastQuestion.after(event.data.newQuestionRenderedTemplate);
            } else {
                this.$el.prepend(event.data.newQuestionRenderedTemplate);
            }
            this.quiz.questionsCount++;
            event.data.questionFormWidget.destroy();
            this.$('.o_wslides_js_quiz_add_question').removeClass('d-none');
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
                    this.$('.o_wslides_js_quiz_add_question').removeClass('d-none');
                } else {
                    this.$('.o_wslides_js_quiz_add_quiz').removeClass('d-none');
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
            this.$('.o_wslides_js_lesson_quiz_question[data-question-id=' + questionId + ']').remove();
            this.quiz.questionsCount--;
            this._reorderQuestions();
            var $newQuestionSequence = this.$('.o_wslides_js_lesson_quiz_new_question .o_wslides_quiz_question_sequence');
            $newQuestionSequence.text(parseInt($newQuestionSequence.text()) - 1);
            if (this.quiz.questionsCount === 0 && !this.$('.o_wsildes_quiz_question_input').length) {
                this.$('.o_wslides_js_quiz_add_quiz').removeClass('d-none');
                this.$('.o_wslides_js_quiz_add_question').addClass('d-none');
                this.$('.o_wslides_js_lesson_quiz_validation').addClass('d-none');
            }
        },
    });

    /**
     * Dialog box shown when clicking the deletion button on a Question.
     * When confirming it sends a RPC request to delete the Question.
     */
    var ConfirmationDialog = Dialog.extend({
        template: 'slide.quiz.confirm.deletion',
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
                model: 'slide.question',
                method: 'unlink',
                args: [this.questionId],
            }).then(function () {
                self.trigger_up('delete_question', { questionId: self.questionId });
                self.close();
            });
        }
    });

    publicWidget.registry.websiteSlidesQuizNoFullscreen = SlideCoursePage.extend({
        selector: '.o_wslides_lesson_main', // selector of complete page, as we need slide content and aside content table
        custom_events: _.extend({}, SlideCoursePage.prototype.custom_events, {
            slide_go_next: '_onQuizNextSlide',
        }),

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @override
         * @param {Object} parent
         */
        start: function () {
            const ret = this._super(...arguments);

            const $quiz = this.$('.o_wslides_js_lesson_quiz');
            if ($quiz.length) {
                const slideData = $quiz.data();
                const channelData = this._extractChannelData(slideData);
                slideData.quizData = {
                    questions: this._extractQuestionsAndAnswers(),
                    sessionAnswers: slideData.sessionAnswers || [],
                    quizKarmaMax: slideData.quizKarmaMax,
                    quizKarmaWon: slideData.quizKarmaWon || 0,
                    quizKarmaGain: slideData.quizKarmaGain,
                    quizAttemptsCount: slideData.quizAttemptsCount,
                };

                this.quiz = new Quiz(this, slideData, channelData, slideData.quizData);
                this.quiz.attachTo($quiz);
            } else {
                this.quiz = null;
            }
            return ret;
        },

        //----------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------
        _onQuizNextSlide: function () {
            var url = this.$('.o_wslides_js_lesson_quiz').data('next-slide-url');
            window.location.replace(url);
        },

        //----------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * Get the slide data from the elements in the DOM.
         *
         * We need this overwrite because a documentation in non-fullscreen view
         * doesn't have the standard "done" button and so in that case the slide
         * data can not be retrieved.
         *
         * @override
         * @param {Integer} slideId
         */
        _getSlide: function (slideId) {
            const slide = this._super(...arguments);
            if (slide) {
                return slide;
            }
            // A quiz in a documentation on non fullscreen view
            return $(`.o_wslides_js_lesson_quiz[data-id="${slideId}"`).data();
        },

        /**
         * After a slide has been marked as completed / uncompleted, update the state
         * of this widget and reload the slide if needed (e.g. to re-show the questions
         * of a quiz).
         *
         * @override
         * @param {Object} slide
         * @param {Boolean} completed
         */
        toggleCompletionButton: function (slide, completed = true) {
            this._super(...arguments);

            if (this.quiz && this.quiz.slide.id === slide.id && !completed && this.quiz.quiz.questionsCount) {
                // The quiz has been marked as "Not Done", re-load the questions
                this.quiz.quiz.answers = null;
                this.quiz.quiz.sessionAnswers = null;
                this.quiz.slide.completed = false;
                this.quiz._fetchQuiz().then(() => {
                    this.quiz.renderElement();
                    this.quiz._renderValidationInfo();
                });

            }

            // The quiz has been submitted in a documentation and in non fullscreen view,
            // should update the button "Mark Done" to "Mark To Do"
            const $doneButton = $('.o_wslides_done_button');
            if ($doneButton.length && completed) {
                $doneButton
                    .removeClass('o_wslides_done_button disabled btn-primary text-white')
                    .addClass('o_wslides_undone_button btn-light')
                    .text(_t('Mark To Do'))
                    .removeAttr('title')
                    .removeAttr('aria-disabled')
                    .attr('href', `/slides/slide/${slide.id}/set_uncompleted`);
            }
        },

        _extractChannelData: function (slideData) {
            return {
                channelId: slideData.channelId,
                channelEnroll: slideData.channelEnroll,
                channelRequestedAccess: slideData.channelRequestedAccess || false,
                signupAllowed: slideData.signupAllowed
            };
        },

        /**
         * Extract data from exiting DOM rendered server-side, to have the list of questions with their
         * relative answers.
         * This method should return the same format as /slide/quiz/get controller.
         *
         * @return {Array<Object>} list of questions with answers
         */
        _extractQuestionsAndAnswers: function () {
            var questions = [];
            this.$('.o_wslides_js_lesson_quiz_question').each(function () {
                var $question = $(this);
                var answers = [];
                $question.find('.o_wslides_quiz_answer').each(function () {
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

    export var Quiz = Quiz;
    export var ConfirmationDialog = ConfirmationDialog;
    export const websiteSlidesQuizNoFullscreen = publicWidget.registry.websiteSlidesQuizNoFullscreen;
