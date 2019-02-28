odoo.define('website_slides.quiz', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');

    var QWeb = core.qweb;

    var Quiz= publicWidget.Widget.extend({
         /**
        * @override
        * @param {Object} el
        * @param {Object} data holding all the slide elements needed for the quiz
        * It will either come from the fullscreen widget or the sAnimation at the end of this file
        */
        init: function (el, data, nextSlide){
            this.slide = data;
            this.nextSlide = nextSlide;
            this.answeredQuestions = [];
            this.fullscreen = el;
            return this._super.apply(this,arguments);
        },
        start: function (){
            var self = this;
            self._bindQuizEvents();
            /**
             * If the quiz is rendered by the server instead of the fullscreen widget,
             * questions and their answers will have to be created manually from attributes
             */
            if (self.slide.quiz.questions.length === 0){
                this._setQuestions();
            }
            return this._super.apply(this, arguments);
        },
        _renderSuccessModal: function (data){
            var self =this;
            $('.o_wslides_fs_quiz').append(QWeb.render('website.course.quiz.success', {
                data: data,
                nextSlide: self.nextSlide
            }));
            $('.submit-quiz').remove();
            $('.next-slide').css('display', 'inline-block');
            $('.next-slide').click(function (){
                self.fullscreen._goToNextSlide();
            });
            $('.o_wslides_quiz_success_modal_close').click(function (){
                $('.o_wslides_quiz_success_modal').remove();
                $('.o_wslides_quiz_modal_background').remove();
            });
            $(".o_wslides_quiz_modal_background").click(function (ev){
                $(ev.currentTarget).remove();
                $('.o_wslides_quiz_success_modal').remove();
            });
        },
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
        * @private
        * In case the quiz is rendered by the server and the data don't come from the fullscreen widget,
        * questions and their answers will have to be set here by using attributes
        */
        _setQuestions: function (){
            var self = this;
            $('.o_wslides_quiz_question').each(function (){
                self.slide.quiz.questions.push({
                    id: parseInt($(this).attr('id')),
                    title: $(this).attr('title'),
                    answers: []
                });
            });
            for (var i = 0; i < self.slide.quiz.questions.length; i++){
                self._setAnswersForQuestion(self.slide.quiz.questions[i]);
            }
        },
        _setAnswersForQuestion: function (question){
            $('.o_wslides_quiz_answer[question_id='+question.id+']').each(function (){
                question.answers.push({
                    id: parseInt($(this).attr('id')),
                    text: $(this).attr('text_value'),
                    is_correct: $(this).attr('is_correct')
                });
            });
        },
        _updateProgressbar: function (){
            var self = this;
            var completion = self.channelCompletion <= 100 ? self.channelCompletion : 100;
            $('.o_wslides_fs_sidebar_progress_gauge').css('width', completion + "%" );
            $('.o_wslides_progress_percentage').text(completion);
        },
        _bindQuizEvents: function (){
            var self = this;
            if (!self.slide.done){
                $('.o_wslides_quiz_answer').each(function (){
                    $(this).click(self._onAnswerClick.bind(self));
                });
            }
            $('.submit-quiz').click(self._onSubmitQuiz.bind(self));
        },
        _highlightAnswers: function (answers){
            var self = this;
            self.answeredQuestions = [];
            for (var i = 0; i < answers.goodAnswers.length; i++){
                $('#answer'+ answers.goodAnswers[i] +'').addClass('o_wslides_quiz_good_answer');
                $('#answer'+ answers.goodAnswers[i] +' .o_wslides_quiz_radio_box span').replaceWith($('<i class="fa fa-check-circle"></i>'));
                var questionID =$('#answer'+ answers.goodAnswers[i] +' .o_wslides_quiz_radio_box input').attr('question_id');
                self.answeredQuestions.push(questionID);
                $('.o_wslides_quiz_answer[question_id='+questionID+']:not(.o_wslides_quiz_good_answer)').addClass('o_wslides_quiz_ignored_answer');
                $('.o_wslides_quiz_answer[question_id='+questionID+']').each(function (){
                    $(this).unbind('click');
                });
                $('input[question_id='+questionID+']').each(function (){
                    $(this).prop('disabled',true);
                });
            }
            for (i = 0; i < answers.badAnswers.length; i++){
                $('#answer'+ answers.badAnswers[i]).removeClass('o_wslides_quiz_good_answer')
                    .addClass('o_wslides_quiz_bad_answer')
                    .unbind('click');
                $('#answer'+ answers.badAnswers[i] +' .o_wslides_quiz_radio_box span').replaceWith($('<i class="fa fa-times "></i>'));
                $('#answer'+ answers.badAnswers[i] +' .o_wslides_quiz_radio_box input').prop('checked', false);
            }
        },
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        _onAnswerClick: function (ev){
            var self = this;
            var target = $(ev.currentTarget);
            if ((self.answeredQuestions.indexOf(target.attr('question_id'))) === -1){
                var id = target.attr('id');
                var question_id = target.attr('question_id');
                $('.o_wslides_quiz_answer[question_id='+question_id+']').removeClass('o_wslides_quiz_good_answer');
                $('#'+id+' input[type=radio]').prop('checked', true);
            }
        },
        _onSubmitQuiz: function (){
            var self = this;
            var inputs = $('input[type=radio]:checked');
            var values = [];
            for (var i = 0; i < inputs.length; i++){
                values.push(parseInt($(inputs[i]).val()));
            }
            if (values.length === self.slide.quiz.questions.length){
                $('.quiz-danger').remove();
                self._rpc({
                    route: "/slide/quiz/submit",
                    params: {
                        slide_id: self.slide.id,
                        answer_ids: values,
                        quiz_id: self.slide.quiz_id
                    }
                }).then(function (data){
                    self._highlightAnswers(data);
                    self.slide.quiz.nb_attempts = data.attempts_count;
                    if (data.passed){
                        self.channelCompletion = data.channel_completion;
                        self._updateProgressbar();
                        $('#check-'+self.slide.id).replaceWith($('<i class="check-done o_wslides_slide_completed fa fa-check-circle"></i>'));
                        self.slide.done = true;
                        self._renderSuccessModal(data);
                    }
                    else {
                        var points = self.slide.quiz.nb_attempts < self.slide.quiz.possible_rewards.length ? self.slide.quiz.possible_rewards[self.slide.quiz.nb_attempts] : self.slide.quiz.possible_rewards[self.slide.quiz.possible_rewards.length-1];
                        $('#quiz-points').text(points);
                    }
                });
            } else {
                $('#quiz_buttons').append($('<p class="quiz-danger text-danger mt-1">All questions must be answered !</p>'));
            }
        },
});

    publicWidget.registry.websiteSlidesQuizNoFullscreen = publicWidget.Widget.extend({
        selector: '.o_w_slides_quiz_no_fullscreen',
        xmlDependencies: ['/website_slides/static/src/xml/website_slides_fullscreen.xml'],
        init: function (el){
            this._super.apply(this, arguments);
        },
        start: function (){
            this._super.apply(this, arguments);
            var slideID = parseInt(this.$el.attr('slide_id'),10);
            var slideDone = this.$el.attr('slide_done');
            var nbAttempts = parseInt(this.$el.attr('nb_attempts'), 10);
            var firstAttemptReward = this.$el.attr('first_reward');
            var secondAttemptReward = this.$el.attr('second_reward');
            var thirdAttemptReward = this.$el.attr('third_reward');
            var fourthAttemptReward = this.$el.attr('fourth_reward');
            var possibleRewards = [firstAttemptReward,secondAttemptReward,thirdAttemptReward,fourthAttemptReward];
            var data = {
                id: slideID,
                done: slideDone,
                quiz: {
                    questions: [],
                    nb_attempts: nbAttempts,
                    possible_rewards: possibleRewards,
                    reward: nbAttempts < possibleRewards.length ? possibleRewards[nbAttempts] : possibleRewards[possibleRewards.length-1]
                }
            };
            if (!slideDone){
                var NewQuiz = new Quiz(this, data);
                NewQuiz.appendTo(".o_w_slides_quiz_no_fullscreen");
            }
        }
    });

    return Quiz;
});
