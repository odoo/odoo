odoo.define('website_slides.quiz', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var session = require('web.session');

    var CourseJoinWidget = require('website_slides.course.join.widget').courseJoinWidget;
    var QuestionFormWidget = require('website_slides.quiz.question.form');

    var QWeb = core.qweb;
    var _t = core._t;

    /**
     * This widget is responsible of displaying quiz questions and propositions. Submitting the quiz will fetch the
     * correction and decorate the answers according to the result. Error message or modal can be displayed.
     *
     * This widget can be attached to DOM rendered server-side by `website_slides.slide_type_quiz` or
     * used client side (Fullscreen).
     *
     * Triggered events are :
     * - slide_go_next: need to go to the next slide, when quiz is done. Event data contains the current slide id.
     * - quiz_completed: when the quiz is passed and completed by the user. Event data contains current slide data.
     */
    var Quiz = publicWidget.Widget.extend({
        template: 'slide.slide.quiz',
        xmlDependencies: ['/website_slides/static/src/xml/slide_quiz.xml'],
        events: {
            "click .o_wslides_quiz_answer": '_onAnswerClick',
            "click .o_wslides_js_lesson_quiz_submit": '_onSubmitQuiz',
            "click .o_wslides_quiz_modal_btn": '_onClickNext',
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
         * @override
         * At the end we set self.slide.answers = false so that if you retry the quiz because it was wrongly answered
         * _renderAnswersHighlighting correctly render the corrections. If self.slide.answers still contains value,
         * those radiobuttons will be checked again as well as the new answers.
         */
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function ()  {
                self._renderAnswers();
                self._renderAnswersHighlighting();
                self._renderValidationInfo();
                self._bindSortable();
                self._checkLocationHref();
                if (!self.isMember) {
                    self._renderJoinWidget();
                } else if (!self.publicUser && self.slide.answers) {
                    var values = self._getAnswers();
                    self._submitQuiz(values);
                }
                self.slide.answers = false;
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * @private
         */
        _alertShow: function (alert_code) {
            var message = _t('There was an error validating this quiz.');
            if (alert_code === 'slide_quiz_incomplete') {
                message = _t('All questions must be answered !');
            } else if (alert_code === 'slide_quiz_done') {
                message = _t('This quiz is already done. Retaking it is not possible.');
            } else if (alert_code === 'public_user') {
                message = _t('You must be logged to submit the quiz.');
            }
            this.displayNotification({
                type: 'warning',
                title: _t('Something went wrong'),
                message: message,
                sticky: true
            });
        },

        /**
         * Allows to reorder the questions
         * @private
         */
        _bindSortable: function() {
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
        _renderAnswers: function () {
            var self = this;
            this.$('input[type=radio]').each(function () {
                $(this).prop('disabled', self.slide.completed);
            });
        },

        /**
         * @private
         * Decorate the answer inputs according to the correction
         */
        _renderAnswersHighlighting: function () {
            var self = this;
            this.$('a.o_wslides_quiz_answer').each(function () {
                var $answer = $(this);
                var answerId = $answer.data('answerId');
                if (_.contains(self.quiz.goodAnswers, answerId)) {
                    $answer.removeClass('list-group-item-danger').addClass('list-group-item-success');
                    $answer.find('i.fa').addClass('d-none');
                    $answer.find('i.fa-check-circle').removeClass('d-none');
                    $answer.find('input[type=radio]').prop('checked', true);
                }
                else if (_.contains(self.quiz.badAnswers, answerId)) {
                    $answer.removeClass('list-group-item-success').addClass('list-group-item-danger');
                    $answer.find('i.fa').addClass('d-none');
                    $answer.find('i.fa-times-circle').removeClass('d-none');
                    $answer.find('label input').prop('checked', false);
                    $answer.find('input[type=radio]').prop('checked', true);
                }
                else if (!self.slide.completed) {
                    if (_.contains(self.slide.answers, answerId)) {
                        $answer.find('i.fa').addClass('d-none');
                        $answer.find('input[type=radio]').prop('checked', true);
                        $answer.find('i.fa-circle').removeClass('d-none');
                    } else {
                        $answer.removeClass('list-group-item-danger list-group-item-success');
                        $answer.find('i.fa').addClass('d-none');
                        $answer.find('input[type=radio]').prop('checked', false);
                        $answer.find('i.fa-circle').removeClass('d-none');
                    }
                }
            });
        },

        /**
         * @private
         * When the quiz is done and succeed, a congratulation modal appears.
         */
        _renderSuccessModal: function () {
            var $modal = this.$('#slides_quiz_modal');
            if (!$modal.length) {
                this.$el.append(QWeb.render('slide.slide.quiz.finish', {'widget': this}));
                $modal = this.$('#slides_quiz_modal');
            }
            var self = this;
            $modal.on('shown.bs.modal', function () {
                var rankProgress = self.quiz.rankProgress;
                self._animateText($modal, rankProgress);
                self._animateProgressBar($modal, rankProgress);
            });
            $modal.modal({
                'show': true,
            });
            $modal.on('hidden.bs.modal', function () {
                $modal.remove();
            });
        },

        /**
         * Handles the animation of the karma gain in the following steps:
         * 1. Initiate the tooltip which will display the actual Karma
         *    over the progress bar.
         * 2. Animate the tooltip text to increment smoothly from the old
         *    karma value to the new karma value and updates it to make it
         *    move as the progress bar moves.
         * 3a. The user doesn't level up
         *    I.   When the user doesn't level up the progress bar simply goes
         *         from the old karma value to the new karma value.
         * 3b. The user levels up
         *    I.   The first step makes the progress bar go from the old karma
         *         value to 100%.
         *    II.  The second step makes the progress bar go from 100% to 0%.
         *    III. The third and final step makes the progress bar go from 0%
         *         to the new karma value. It also changes the lower and upper
         *         bound to match the new rank.
         * @param $modal
         * @param rankProgress
         * @private
         */
        _animateProgressBar: function ($modal, rankProgress) {
            var self = this;

            this.$('[data-toggle="tooltip"]').tooltip({
                trigger: 'manual',
                container: '.progress-bar-tooltip',
            }).tooltip('show');

            $modal.find('.tooltip-inner')
                .prop('karma', rankProgress.previous_rank.karma)
                .animate({
                    karma: rankProgress.new_rank.karma
                }, {
                    duration: rankProgress.level_up ? 1700 : 800,
                    step: function (newKarma) {
                        $modal.find('.tooltip-inner').text(Math.ceil(newKarma));
                        self.$('[data-toggle="tooltip"]').tooltip('update');
                    }
                }
            );

            var $progressBar = $modal.find('.progress-bar');
            if (rankProgress.level_up) {
                $modal.find('.o_wslides_quiz_modal_title').text(_('Level up!'));
                $progressBar.css('width', '100%');
                _.delay(function () {
                    $modal.find('.o_wslides_quiz_modal_rank_lower_bound')
                        .text(rankProgress.new_rank.lower_bound);
                    $modal.find('.o_wslides_quiz_modal_rank_upper_bound')
                        .text(rankProgress.new_rank.upper_bound || "");

                    // we need to use _.delay to force DOM re-rendering between 0 and new percentage
                    _.delay(function () {
                        $progressBar.addClass('no-transition').width('0%');
                    }, 1);
                    _.delay(function () {
                        $progressBar
                            .removeClass('no-transition')
                            .width(rankProgress.new_rank.progress + '%');
                    }, 100);
                }, 800);
            } else {
                $progressBar.css('width', rankProgress.new_rank.progress + '%');
            }
        },

        _animateText: function ($modal, rankProgress) {
           _.delay(function () {
                $modal.find('h4.o_wslides_quiz_modal_xp_gained').addClass('show in');
                $modal.find('.o_wslides_quiz_modal_dismiss').removeClass('d-none');
            }, 800);

            if (rankProgress.level_up) {
                _.delay(function () {
                    $modal.find('.o_wslides_quiz_modal_rank_motivational').addClass('fade');
                    _.delay(function () {
                        $modal.find('.o_wslides_quiz_modal_rank_motivational').html(
                            rankProgress.last_rank ?
                                rankProgress.description :
                                rankProgress.new_rank.motivational
                        );
                        $modal.find('.o_wslides_quiz_modal_rank_motivational').addClass('show in');
                    }, 800);
                }, 800);
            }
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

        /*
         * @private
         * render the button to join a course. If the user is logged in,
         * the course is public, and the user has previously tried to submit
         * answers, the course will be automatically joined.
         */
        _renderJoinWidget: function () {
            var options = {
                isQuiz: true,
                channel: this.channel,
                isMember: this.isMember,
                publicUser: this.publicUser,
                beforeJoin: this._saveQuizAnswers.bind(this),
                afterJoin: this._afterJoin.bind(this),         
            };
            var courseJoinWidget = new CourseJoinWidget(this, options);
            var $widgetLocation = this.$(".o_wslides_join_course_widget");
            if ($widgetLocation.length !== 0) {
                courseJoinWidget.appendTo(this.$(".o_wslides_join_course_widget"));
                if (!this.publicUser && courseJoinWidget.channel.channelEnroll === 'public' && this.slide.answers) {
                        courseJoinWidget.joinChannel(this.channel.channelId);
                }
            }
        },

        /**
         * Get the answers filled in by the User
         *
         * @private
         */
        _getAnswers: function () {
            return this.$('input[type=radio]:checked').map(function (index, element) {
                return parseInt($(element).val());
            }).get();
        },

        /*
         * Submit the given answer, and display the result
         *
         * @param Array checkedAnswers: list of checked answers
         */
        _submitQuiz: function (checkedAnswers) {
            var self = this;
            return this._rpc({
                route: '/slides/slide/quiz/submit',
                params: {
                    slide_id: self.slide.id,
                    answer_ids: checkedAnswers,
                }
            }).then(function (data) {
                if (data.error) {
                    self._alertShow(data.error);
                } else {
                    self.quiz = _.extend(self.quiz, data);
                    if (data.completed) {
                        self._renderSuccessModal(data);
                        self.slide.completed = true;
                        self.trigger_up('slide_completed', {slide: self.slide, completion: data.channel_completion});
                    }
                    self._hideEditOptions();
                    self._renderAnswersHighlighting();
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
            $elem.find('.o_wslides_quiz_answer').each(function () {
                answers.push({
                    'id': $(this).data('answerId'),
                    'text_value': $(this).data('text'),
                    'is_correct': $(this).data('isCorrect')
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
                if (this.$('#slides_quiz_modal').length !== 0) {
                    this.$('#slides_quiz_modal').modal('hide');
                }
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
         * Submit a quiz and get the correction. It will display messages
         * according to quiz result.
         *
         * @private
         * @param
         */
        _onSubmitQuiz: function () {
            var values = this._getAnswers();
            this._submitQuiz(values);
        },
            
        /**
         * Saves the answers from the user and redirect the user to the
         * specified url
         *
         * @private
         */
        _saveQuizAnswers: function () {
            var quizAnswers = this._getAnswers();
            if (quizAnswers.length === this.quiz.questions.length) {
                return this._rpc({
                    route: '/slides/slide/quiz/save_slide_answers',
                    params: {
                        'quiz_answers': {'slide_id': this.slide.id, 'slide_answers': quizAnswers},
                    }
                });
            } else {
                this._alertShow('slide_quiz_incomplete');
                return Promise.resolve();
            }
        },
        /* Submit a quiz and get the correction, after joining the course
        *
        * @private
        */
       _afterJoin: function () {
            this.isMember = true;
            this._renderValidationInfo();
            var values = this._getAnswers();
            this._submitQuiz(values);
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
            if (event.data.save_and_new) {
                this._onCreateQuizClick();
            } else {
                this.$('.o_wslides_js_quiz_add_question').removeClass('d-none');
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
        xmlDependencies: Dialog.prototype.xmlDependencies.concat(
            ['/website_slides/static/src/xml/slide_quiz_create.xml']
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
                model: 'slide.question',
                method: 'unlink',
                args: [this.questionId],
            }).then(function () {
                self.trigger_up('delete_question', { questionId: self.questionId });
                self.close();
            });
        }
    });

    publicWidget.registry.websiteSlidesQuizNoFullscreen = publicWidget.Widget.extend({
        selector: '.o_wslides_lesson_main', // selector of complete page, as we need slide content and aside content table
        custom_events: {
            slide_go_next: '_onQuizNextSlide',
            slide_completed: '_onQuizCompleted',
        },

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
            this.$('.o_wslides_js_lesson_quiz').each(function () {
                var slideData = $(this).data();
                var channelData = self._extractChannelData(slideData);
                slideData.quizData = {
                    questions: self._extractQuestionsAndAnswers(),
                    answers: slideData.answers || [],
                    quizKarmaMax: slideData.quizKarmaMax,
                    quizKarmaWon: slideData.quizKarmaWon,
                    quizKarmaGain: slideData.quizKarmaGain,
                    quizAttemptsCount: slideData.quizAttemptsCount,
                };
                defs.push(new Quiz(self, slideData, channelData, slideData.quizData).attachTo($(this)));
            });
            return Promise.all(defs);
        },

        //----------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------
        _onQuizCompleted: function (ev) {
            var slide = ev.data.slide;
            var completion = ev.data.completion;
            this.$('#o_wslides_lesson_aside_slide_check_' + slide.id).addClass('text-success fa-check').removeClass('text-600 fa-circle-o');
            // need to use global selector as progress bar is outside this animation widget scope
            $('.o_wslides_lesson_header .progress-bar').css('width', completion + "%");
            $('.o_wslides_lesson_header .progress span').text(_.str.sprintf("%s %%", completion));
        },
        _onQuizNextSlide: function () {
            var url = this.$('.o_wslides_js_lesson_quiz').data('next-slide-url');
            window.location.replace(url);
        },

        //----------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        _extractChannelData: function (slideData) {
            return {
                channelId: slideData.channelId,
                channelEnroll: slideData.channelEnroll,
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

    return {
        Quiz: Quiz,
        ConfirmationDialog: ConfirmationDialog,
        websiteSlidesQuizNoFullscreen: publicWidget.registry.websiteSlidesQuizNoFullscreen
    };
});
