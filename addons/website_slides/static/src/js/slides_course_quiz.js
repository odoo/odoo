odoo.define('website_slides.quiz', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var session = require('web.session');

    var CourseJoinWidget = require('website_slides.course.join.widget').courseJoinWidget;

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
    var Quiz= publicWidget.Widget.extend({
        template: 'slide.slide.quiz',
        xmlDependencies: ['/website_slides/static/src/xml/slide_quiz.xml'],
        events: {
            "click .o_wslides_quiz_answer": '_onAnswerClick',
            "click .o_wslides_js_lesson_quiz_submit": '_onSubmitQuiz',
            "click .o_wslides_quiz_btn": '_onClickNext',
            "click .o_wslides_quiz_continue": '_onClickNext'
        },

        /**
        * @override
        * @param {Object} parent
        * @param {Object} slide_data holding all the classic slide informations
        * @param {Object} quiz_data : optional quiz data to display. If not given, will be fetched. (questions and answers).
        */
        init: function (parent, slide_data, channel_data, quiz_data) {
            this.slide = _.defaults(slide_data, {
                id: 0,
                name: '',
                hasNext: false,
                completed: false,
                readonly: false,
            });
            this.quiz = quiz_data || false;
            this.readonly = slide_data.readonly || false;
            this.publicUser = session.is_website_user;
            this.redirectURL = encodeURIComponent(document.URL);
            this.channel = channel_data;
            return this._super.apply(this, arguments);
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
         */
        start: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function ()  {
                self._renderAnswers();
                self._renderAnswersHighlighting();
                self._renderValidationInfo();
                new CourseJoinWidget(self, self.channel.channelId).appendTo(self.$('.o_wslides_course_join_widget'));
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _alertHide: function () {
            this.$('.o_wslides_js_lesson_quiz_error').addClass('d-none');
        },

        _alertShow: function (alert_code) {
            var message = _t('There was an error validating this quiz.');
            if (! alert_code || alert_code === 'slide_quiz_incomplete') {
                message = _t('All questions must be answered !');
            }
            else if (alert_code === 'slide_quiz_done') {
                message = _t('This quiz is already done. Retaking it is not possible.');
            }
            else if (alert_code === 'public_user') {
                message = _t('You must be logged to submit the quiz.');
            }
            this.$('.o_wslides_js_lesson_quiz_error span:first').html(message);
            this.$('.o_wslides_js_lesson_quiz_error').removeClass('d-none');
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
                    quizAttemptsCount: quiz_data.quiz_attempts_count || 0,
                    quizKarmaGain: quiz_data.quiz_karma_gain || 0,
                    quizKarmaWon: quiz_data.quiz_karma_won || 0,
                };
            });
        },

        /**
         * @private
         * Decorate the answers according to state
         */
        _renderAnswers: function () {
            var self = this;
            this.$('input[type=radio]').each(function () {
                $(this).prop('disabled', self.slide.readonly || self.slide.completed);
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
                }
                else if (_.contains(self.quiz.badAnswers, answerId)) {
                    $answer.removeClass('list-group-item-success').addClass('list-group-item-danger');
                    $answer.find('i.fa').addClass('d-none');
                    $answer.find('i.fa-times-circle').removeClass('d-none');
                    $answer.find('label input').prop('checked', false);
                }
                else {
                    if (!self.slide.completed) {
                        $answer.removeClass('list-group-item-danger list-group-item-success');
                        $answer.find('i.fa').addClass('d-none');
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
            $modal.modal({
                'show': true,
            });
            $modal.on('hidden.bs.modal', function () {
                $modal.remove();
            });
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
         * Submit the given answer, and display the result
         *
         * @param Array checkedAnswerIds: list of checked answers
         */
        _submitQuiz: function (checkedAnswerIds) {
            var self = this;
            return this._rpc({
                route: '/slides/slide/quiz/submit',
                params: {
                    slide_id: self.slide.id,
                    answer_ids: checkedAnswerIds,
                }
            }).then(function(data){
                if (data.error) {
                    self._alertShow(data.error);
                } else {
                    self.quiz = _.extend(self.quiz, data);
                    if (data.completed) {
                        self._renderSuccessModal(data);
                        self.slide.completed = true;
                        self.trigger_up('slide_completed', {slide: self.slide, completion: data.channel_completion});
                    }
                    self._renderAnswersHighlighting();
                    self._renderValidationInfo();
                }
            });
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
            if (! this.slide.readonly && ! this.slide.completed) {
                $(ev.currentTarget).find('input[type=radio]').prop('checked', true);
            }
            this._alertHide();
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
         * Submit a quiz and get the correction. It will display messages
         * according to quiz result.
         *
         * @private
         * @param OdooEvent ev
         */
        _onSubmitQuiz: function (ev) {
            var inputs = this.$('input[type=radio]:checked');
            var values = [];
            for (var i = 0; i < inputs.length; i++){
                values.push(parseInt($(inputs[i]).val()));
            }

            if (values.length === this.quiz.questions.length){
                this._alertHide();
                this._submitQuiz(values);
            } else {
                this._alertShow();
            }
        },
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
            var self = this;
            var slide = ev.data.slide;
            var completion = ev.data.completion;
            this.$('#o_wslides_lesson_aside_slide_check_' + slide.id).addClass('text-success fa-check').removeClass('text-600 fa-circle-o');
            // need to use global selector as progress bar is ouside this animation widget scope
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

        _extractChannelData: function (slideData){
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
        _extractQuestionsAndAnswers: function() {
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
                    answers: answers,
                });
            });
            return questions;
        },
    });

    return Quiz;
});
