/** @odoo-module **/

    import publicWidget from '@web/legacy/js/public/public_widget';
    import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
    import { renderToElement } from "@web/core/utils/render";
    import { escape } from "@web/core/utils/strings";
    import { session } from "@web/session";
    import CourseJoin from '@website_slides/js/slides_course_join';
    import QuestionFormWidget from '@website_slides/js/slides_course_quiz_question_form';
    import { SlideCoursePage } from '@website_slides/js/slides_course_page';
    import { rpc } from "@web/core/network/rpc";
    import { SlideQuizFinishDialog } from "@website_slides/js/public/components/slide_quiz_finish_dialog/slide_quiz_finish_dialog";

    import { _t } from "@web/core/l10n/translation";

    import { markup } from "@odoo/owl";

    const CourseJoinWidget = CourseJoin.courseJoinWidget;

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
            "click .o_wslides_quiz_continue": '_onClickNext',
            "click .o_wslides_js_lesson_quiz_reset": '_onClickReset',
            'click .o_wslides_js_quiz_add': '_onCreateQuizClick',
            'click .o_wslides_js_quiz_edit_question': '_onEditQuestionClick',
            'click .o_wslides_js_quiz_delete_question': '_onDeleteQuestionClick',
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
            this.slide = Object.assign({
                id: 0,
                name: '',
                hasNext: false,
                completed: false,
                isMember: false,
                isMemberOrInvited: false,
            }, slide_data);
            this.quiz = quiz_data || false;
            if (this.quiz) {
                this.quiz.questionsCount = quiz_data.questions.length;
            }
            this.isMember = slide_data.isMember || false;
            this.isMemberOrInvited = slide_data.isMemberOrInvited || false;
            this.publicUser = session.is_website_user;
            this.userId = session.user_id;
            this.redirectURL = encodeURIComponent(document.URL);
            this.channel = channel_data;

            this.orm = this.bindService("orm");
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

        destroy() {
            this._unbindSortable();
            return this._super(...arguments);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _showErrorMessage: function (errorCode) {
            var message = _t('There was an error validating this quiz.');
            if (errorCode === 'slide_quiz_incomplete') {
                message = _t('All questions must be answered!');
            } else if (errorCode === 'slide_quiz_done') {
                message = _t('This quiz is already done. Retaking it is not possible.');
            } else if (errorCode === 'public_user') {
                message = _t('You must be logged to submit the quiz.');
            }

            const errorEl = this.el.querySelector('.o_wslides_js_quiz_submit_error');
            errorEl.classList.remove('d-none');
            errorEl.querySelector('.o_wslides_js_quiz_submit_error_text').textContent = message;
        },

        _hideErrorMessage: function () {
            this.el.querySelector('.o_wslides_js_quiz_submit_error').classList.add('d-none');
        },

        /**
         * Allows to reorder the questions
         * @private
         */
        _bindSortable: function () {
            this.bindedSortable = this.call(
                "sortable",
                "create",
                {
                    ref: { el: this.el },
                    handle: ".o_wslides_js_quiz_sequence_handler",
                    elements: ".o_wslides_js_lesson_quiz_question",
                    onDrop: this._reorderQuestions.bind(this),
                    clone: false,
                    placeholderClasses: ['o_wslides_js_quiz_sequence_highlight', 'position-relative', 'my-3'],
                    applyChangeOnDrop: true
                },
            ).enable();
        },

        _unbindSortable: function () {
            this.bindedSortable?.cleanup();
        },

        /**
         * Get all the questions ID from the displayed Quiz
         * @returns {Array}
         * @private
         */
        _getQuestionsIds: function () {
            return [...this.el.querySelectorAll('.o_wslides_js_lesson_quiz_question')].map(function () {
                return this.el.dataset.questionId;
            }).get();
        },

        /**
         * Modify visually the sequence of all the questions after
         * calling the _reorderQuestions RPC call.
         * @private
         */
        _modifyQuestionsSequence: function () {
            this.el.querySelectorAll('.o_wslides_js_lesson_quiz_question').forEach((index, question) => {
                question.querySelector('span.o_wslides_quiz_question_sequence').textContent = index + 1;
            });
        },

        /**
         * RPC call to resequence all the questions. It is called
         * after modifying the sequence of a question and also after
         * deleting a question.
         * @private
         */
        _reorderQuestions: function () {
            rpc('/web/dataset/resequence', {
                model: "slide.question",
                ids: this._getQuestionsIds()
            }).then(this._modifyQuestionsSequence.bind(this))
        },
        /*
         * @private
         * Fetch the quiz for a particular slide
         */
        _fetchQuiz: function () {
            var self = this;
            return rpc('/slides/slide/quiz/get', {
                'slide_id': self.slide.id,
            }).then(function (quiz_data) {
                self.slide.sessionAnswers = quiz_data.session_answers;
                self.quiz = {
                    description_safe: markup(quiz_data.slide_description),
                    questions: quiz_data.slide_questions || [],
                    questionsCount: quiz_data.slide_questions.length,
                    quizAttemptsCount: quiz_data.quiz_attempts_count || 0,
                    quizKarmaGain: quiz_data.quiz_karma_gain || 0,
                    quizKarmaWon: quiz_data.quiz_karma_won || 0,
                    slideResources: quiz_data.slide_resource_ids || [],
                };
            });
        },

        /**
         * Hide the edit and delete button and also the handler
         * to resequence the question
         * @private
         */
        _hideEditOptions: function () {
            let wSlidesEls = this.el.querySelectorAll('.o_wslides_js_lesson_quiz_question .o_wslides_js_quiz_edit_del, .o_wslides_js_lesson_quiz_question .o_wslides_js_quiz_sequence_handler');
            wSlidesEls.forEach(element => element.classList.add('d-none'));
        },

        /**
         * @private
         * Decorate the answers according to state
         */
        _disableAnswers: function () {
            const self = this;
            this.el.querySelector('.o_wslides_js_lesson_quiz_question').classList.add('completed-disabled');
            this.el.querySelectorAll('input[type=radio]').forEach(() => {
                this.disabled = self.slide.completed;
            });
        },

        /**
         * Decorate the answer inputs according to the correction and adds the answer comment if
         * any.
         *
         * @private
         */
        _renderAnswersHighlightingAndComments: function () {
            const self = this;
            [...this.el.querySelectorAll('.o_wslides_js_lesson_quiz_question')].forEach(() => {
                const question =this;
                const questionId = question.dataset.questionId;
                const isCorrect = self.quiz.answers[questionId].is_correct;
                [...question.querySelectorAll('a.o_wslides_quiz_answer')].forEach(() => {
                    const answer = this;
                    answer.querySelector('i.fa').classList.add('d-none');
                    if (answer.querySelector('input[type=radio]').checked) {
                        if (isCorrect) {
                            answer.classList.remove('list-group-item-danger');
                            answer.classList.add('list-group-item-success');
                            answer.querySelector('i.fa-check-circle').classList.remove('d-none');
                        } else {
                            answer.classList.remove('list-group-item-success');
                            answer.classList.add('list-group-item-danger');
                            answer.querySelector('i.fa-times-circle').classList.remove('d-none');
                            answer.querySelector('label input').checked = false;
                        }
                    } else {
                        answer.classList.remove('list-group-item-danger list-group-item-success');
                        answer.querySelector('i.fa-circle').classList.remove('d-none');
                    }
                });
                const comment = self.quiz.answers[questionId].comment;
                if (comment) {
                    question.querySelector('.o_wslides_quiz_answer_info').classList.remove('d-none');
                    question.querySelector('.o_wslides_quiz_answer_comment').textContent = comment;
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

            const self = this;
            [...this.el.querySelectorAll('.o_wslides_js_lesson_quiz_question')].forEach(() => {
                const question = this;
                question.el.querySelectorAll('a.o_wslides_quiz_answer').forEach(() => {
                    const answer = this;
                    if (!answer.querySelector('input[type=radio]').checked &&
                        self.slide.sessionAnswers.includes(answer.dataset.answerId)) {
                        answer.querySelector('input[type=radio]').checked = true;
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
            const validationElem = this.el.querySelector('.o_wslides_js_lesson_quiz_validation');
            validationElem.innerHTML = '';
            validationElem.appendChild(renderToElement('slide.slide.quiz.validation', {'widget': this}));
        },
        /*
        * Toggle additional resource info box
        *
        * @private
        * @param {Boolean} show - Whether show or hide the information
        */
        _toggleAdditionalResourceInfo: function(show) {
            const resourceInfo = document.getElementsByClassName('o_wslides_js_lesson_quiz_resource_info')[0];
            resourceInfo && (show ? resourceInfo.classList.remove('d-none') : resourceInfo.classList.add('d-none'));
        },
        /**
         * Renders the button to join a course.
         * If the user is logged in, the course is public, and the user has previously tried to
         * submit answers, we automatically attempt to join the course.
         *
         * @private
         */
        _renderJoinWidget: function () {
            var widgetLocation = this.el.querySelector(".o_wslides_join_course_widget");
            if (widgetLocation.length !== 0) {
                var courseJoinWidget = new CourseJoinWidget(this, {
                    isQuiz: true,
                    channel: this.channel,
                    isMember: this.isMember,
                    isMemberOrInvited: this.isMemberOrInvited,
                    publicUser: this.publicUser,
                    beforeJoin: this._saveQuizAnswersToSession.bind(this),
                    afterJoin: this._afterJoin.bind(this),
                    joinMessage: _t('Join & Submit'),
                });

                widgetLocation.appendChild(courseJoinWidget);
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
            return [...this.el.querySelectorAll('input[type=radio]:checked')].map(element => parseInt(element.value)).get();
        },

        /**
         * Submit a quiz and get the correction. It will display messages
         * according to quiz result.
         *
         * @private
         */
         async _submitQuiz() {
            const data = await rpc('/slides/slide/quiz/submit', {
                slide_id: this.slide.id,
                answer_ids: this._getQuizAnswers(),
            });
            if (data.error) {
                this._showErrorMessage(data.error);
                return;
            } else {
                this._hideErrorMessage();
            }
            Object.assign(this.quiz, data);
            const {rankProgress, completed, channel_completion: completion} = this.quiz;
            // three of the rankProgress properties are HTML messages, mark if set
            if ('description' in rankProgress) {
                rankProgress['description'] = markup(rankProgress['description'] || '');
                rankProgress['previous_rank']['motivational'] =
                    markup(rankProgress['previous_rank']['motivational'] || '');
                rankProgress['new_rank']['motivational'] =
                    markup(rankProgress['new_rank']['motivational'] || '');
            }
            if (completed) {
                this._disableAnswers();
                this.call("dialog", "add", SlideQuizFinishDialog, {
                    quiz: this.quiz,
                    hasNext: this.slide.hasNext,
                    onClickNext: (ev) => this._onClickNext(ev),
                    userId: this.userId,
                });
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
            this._toggleAdditionalResourceInfo(!completed);
        },

        /**
         * Get all the question information after clicking on
         * the edit button
         * @param elem
         * @returns {{id: *, sequence: number, text: *, answers: Array}}
         * @private
         */
        _getQuestionDetails: function (elem) {
            const answers = [];
            [...elem.querySelectorAll('.o_wslides_quiz_answer')].forEach(() => {
                answers.push({
                    'id': this.dataset.answerId,
                    'text_value': this.dataset.text,
                    'is_correct': this.dataset.isCorrect,
                    'comment': this.dataset.comment,
                });
            });
            return {
                'id': elem.dataset.questionId,
                'sequence': parseInt(elem.querySelector('.o_wslides_quiz_question_sequence').textContent),
                'text': elem.dataset.title,
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
                ev.currentTarget.querySelectorAll('input[type=radio]').forEach(el => el.checked = true);
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
            rpc('/slides/slide/quiz/reset', {
                slide_id: this.slide.id
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

            return rpc('/slides/slide/quiz/save_to_session', {
                'quiz_answers': {'slide_id': this.slide.id, 'slide_answers': this._getQuizAnswers()},
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
            const elem = this.querySelector('.o_wslides_js_lesson_quiz_new_question');
            this.el.querySelector('.o_wslides_js_quiz_add').classList.add('d-none');
            new QuestionFormWidget(this, {
                slideId: this.slide.id,
                sequence: this.quiz.questionsCount + 1
            }).appendTo(elem);
        },

        /**
         * When clicking on the edit button of a question it
         * initialize a new QuestionFormWidget with the existing
         * question as inputs.
         * @param ev
         * @private
         */
        _onEditQuestionClick: function (ev) {
            const editedQuestion = ev.currentTarget.closest('.o_wslides_js_lesson_quiz_question');
            const question = this._getQuestionDetails(editedQuestion);
            let questionFormWidget = new QuestionFormWidget(this, {
                editedQuestion: editedQuestion,
                question: question,
                slideId: this.slide.id,
                sequence: question.sequence,
                update: true
            });
            editedQuestion.parentNode.insertBefore(questionFormWidget, editedQuestion.nextSibling);
            editedQuestion.style.display = 'none';
        },

        /**
         * When clicking on the delete button of a question it toggles a modal
         * to confirm the deletion. When confirming it sends an RPC request to
         * delete the Question and triggers an event to delete it from the UI.
         * @param ev
         * @private
         */
        _onDeleteQuestionClick: function (ev) {
            const question = ev.currentTarget.closest('.o_wslides_js_lesson_quiz_question');
            const questionId = parseInt(question.dataset.questionId);
            this.call('dialog', 'add', ConfirmationDialog, {
                title: _t('Delete Question'),
                body: markup(_t('Are you sure you want to delete this question "<strong>%s</strong>"?', escape(question.dataset.title))),
                cancel: () => {
                },
                cancelLabel: _t('No'),
                confirm: async () => {
                    await this.orm.unlink('slide.question', [questionId]);
                    this.trigger_up('delete_question', { questionId });
                },
                confirmLabel: _t('Yes'),
            });
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
            const lastQuestion = this.el.querySelector('.o_wslides_js_lesson_quiz_question:last-child');
            if (lastQuestion.length !== 0) {
                lastQuestion.after(event.data.newQuestionRenderedTemplate);
            } else {
                this.el.prepend(event.data.newQuestionRenderedTemplate);
            }
            this.quiz.questionsCount++;
            event.data.questionFormWidget.destroy();
            this.el.querySelector('.o_wslides_js_quiz_add_question').classList.remove('d-none');
        },

        /**
         * Replace the edited question by the new question and destroy
         * the QuestionFormWidget.
         * @param event
         * @private
         */
        _displayUpdatedQuestion: function (event) {
            var questionFormWidget = event.data.questionFormWidget;
            event.data.editedQuestion.replaceWith(event.data.newQuestionRenderedTemplate);
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
            const questionFormWidget = event.data.questionFormWidget;
            if (questionFormWidget.update) {
                questionFormWidget.editedQuestion.display = '';
            } else {
                if (this.quiz.questionsCount > 0) {
                    this.el.querySelector('.o_wslides_js_quiz_add_question').classList.remove('d-none');
                } else {
                    this.el.querySelector('.o_wslides_js_quiz_add_quiz').classList.remove('d-none');
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
            const questionId = event.data.questionId;
            this.el.querySelector('.o_wslides_js_lesson_quiz_question[data-question-id=' + questionId + ']').remove();
            this.quiz.questionsCount--;
            this._reorderQuestions();
            const newQuestionSequence = this.el.querySelector('.o_wslides_js_lesson_quiz_new_question .o_wslides_quiz_question_sequence');
            newQuestionSequence.textContent = (parseInt(newQuestionSequence.textContent) - 1);
            if (this.quiz.questionsCount === 0 && !this.el.querySelector('.o_wsildes_quiz_question_input').length) {
                this.el.querySelector('.o_wslides_js_quiz_add_quiz').classList.remove('d-none');
                this.el.querySelector('.o_wslides_js_quiz_add_question').classList.add('d-none');
                this.el.querySelector('.o_wslides_js_lesson_quiz_validation').classList.add('d-none');
            }
        },
    });

    publicWidget.registry.websiteSlidesQuizNoFullscreen = SlideCoursePage.extend({
        selector: '.o_wslides_lesson_main', // selector of complete page, as we need slide content and aside content table
        custom_events: Object.assign({}, SlideCoursePage.prototype.custom_events, {
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

            const quiz = this.el.querySelector('.o_wslides_js_lesson_quiz');
            if (quiz.length) {
                const slideData = quiz.dataset;
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
                this.quiz.attachTo(quiz);
            } else {
                this.quiz = null;
            }
            return ret;
        },

        //----------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------
        _onQuizNextSlide: function () {
            const url = this.el.querySelector('.o_wslides_js_lesson_quiz').dataset.nextSlideUrl;
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
            return this.el.querySelector(`.o_wslides_js_lesson_quiz[data-id="${slideId}"]`).dataset;
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
            const doneButton = this.el.querySelector('.o_wslides_done_button');
            if (doneButton.length && completed) {
                doneButton.classList.remove('o_wslides_done_button', 'btn-primary', 'text-white');
                doneButton.classList.add('o_wslides_undone_button', 'btn-light');
                doneButton.textContent = _t('Mark To Do');
                doneButton.removeAttribute('title');
                doneButton.removeAttribute('aria-disabled');
                doneButton.setAttribute('href', `/slides/slide/${encodeURIComponent(slide.id)}/set_uncompleted`);
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
            const questions = [];
            this.el.querySelectorAll('.o_wslides_js_lesson_quiz_question').forEach(() => {
                const question = this;
                const answers = [];
                question.querySelectorAll('.o_wslides_quiz_answer').forEach(() => {
                    const answer = this;
                    answers.push({
                        id: answer.dataset.answerId,
                        text: answer.dataset.text,
                    });
                });
                questions.push({
                    id: question.dataset.questionId,
                    title: question.dataset.title,
                    answer_ids: answers,
                });
            });
            return questions;
        },
    });

    export var Quiz = Quiz;
    export const websiteSlidesQuizNoFullscreen = publicWidget.registry.websiteSlidesQuizNoFullscreen;
