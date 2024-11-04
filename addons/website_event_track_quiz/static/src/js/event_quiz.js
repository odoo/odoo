import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { renderToElement } from "@web/core/utils/render";
import { user } from "@web/core/user";

/**
 * This widget is responsible of displaying quiz questions and propositions. Submitting the quiz will fetch the
 * correction and decorate the answers according to the result. Error message can be displayed.
 *
 * This widget can be attached to DOM rendered server-side by `gamification_quiz.`
 *
 */
var Quiz = publicWidget.Widget.extend({
    template: 'quiz.main',
    events: {
        "click .o_quiz_quiz_answer": '_onAnswerClick',
        "click .o_quiz_js_quiz_submit": '_submitQuiz',
        "click .o_quiz_js_quiz_reset": '_onClickReset',
    },

    /**
    * @override
    * @param {Object} parent
    * @param {Object} data holding all the container information
    * @param {Object} quizData : quiz data to display
    */
    init: function (parent, data, quizData) {
        this._super.apply(this, arguments);
        this.track = Object.assign({
            id: 0,
            name: '',
            eventId: '',
            completed: false,
            isMember: false,
            progressBar: false,
            isEventUser: false,
            repeatable: false
        }, data);
        this.quiz = quizData || false;
        if (this.quiz) {
            this.quiz.questionsCount = quizData.questions.length;
        }
        this.isMember = data.isMember || false;
        this.userId = user.userId;
        this.redirectURL = encodeURIComponent(document.URL);

        this.notification = this.bindService("notification");
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
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _alertShow: function (alertCode) {
        var message = _t('There was an error validating this quiz.');
        if (alertCode === 'quiz_incomplete') {
            message = _t('All questions must be answered!');
        } else if (alertCode === 'quiz_done') {
            message = _t('This quiz is already done. Retaking it is not possible.');
        }

        this.notification.add(message, {
            type: 'warning',
            title: _t('Quiz validation error'),
            sticky: true
        });
    },

    /**
     * @private
     * Decorate the answers according to state
     */
    _disableAnswers: function () {
        this.$('.o_quiz_js_quiz_question').addClass('completed-disabled');
        this.$('input[type=radio]').prop('disabled', true);
    },

    /**
     * @private
     * Decorate the answers according to state
     */
    _enableAnswers: function() {
        this.$('.o_quiz_js_quiz_question').removeClass('completed-disabled');
        this.$('input[type=radio]').prop('disabled', false);
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
            var answer = self.quiz.answers[questionId];
            $question.find('a.o_quiz_quiz_answer').each(function () {
                var $answer = $(this);
                $answer.find('i.fa').addClass('d-none');
                if ($answer.find('input[type=radio]').is(':checked')) {
                    if (answer.is_correct) {
                        $answer.find('i.fa-check-circle').removeClass('d-none');
                    } else {
                        $answer.find('label input').prop('checked', false);
                        $answer.find('i.fa-times-circle').removeClass('d-none');
                    }
                    if (answer.awarded_points > 0) {
                        $answer.append(renderToElement('quiz.badge', {'answer': answer}));
                    }
                } else {
                    $answer.find('i.fa-circle').removeClass('d-none');
                }
            });
            var $list = $question.find('.list-group');
            $list.append(renderToElement('quiz.comment', {'answer': answer}));
        });
    },

    /*
        * @private
        * Update validation box (karma, buttons) according to widget state
        */
    _renderValidationInfo: function () {
        var $validationElem = this.$('.o_quiz_js_quiz_validation');
        $validationElem.empty().append(
            renderToElement('quiz.validation', {'widget': this})
        );
    },

    /**
     * Remove the answer decorators
     */
     _resetQuiz: function () {
        this.$('.o_quiz_js_quiz_question').each(function () {
            var $question = $(this);
            $question.find('a.o_quiz_quiz_answer').each(function () {
                var $answer = $(this);
                $answer.find('i.fa').addClass('d-none');
                $answer.find('i.fa-circle').removeClass('d-none');
                $answer.find('span.badge').remove();
                $answer.find('input[type=radio]').prop('checked', false);
            });
            var $info = $question.find('.o_quiz_quiz_answer_info');
            $info.remove();
        });
        this.track.completed = false;
        this._enableAnswers();
        this._renderValidationInfo();
    },

    /**
     * Submit a quiz and get the correction. It will display messages
     * according to quiz result.
     *
     * @private
     */
    _submitQuiz: function () {
        var self = this;

        return rpc('/event_track/quiz/submit', {
            event_id: self.track.eventId,
            track_id: self.track.id,
            answer_ids: this._getQuizAnswers(),
        }).then(function (data) {
            if (data.error) {
                self._alertShow(data.error);
            } else {
                self.quiz = Object.assign(self.quiz, data);
                self.quiz.quizPointsGained = data.quiz_points;
                if (data.quiz_completed) {
                    self._disableAnswers();
                    self.track.completed = data.quiz_completed;
                }
                self._renderAnswersHighlightingAndComments();
                self._renderValidationInfo();
            }

            return Promise.resolve(data);
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
        if (!this.track.completed) {
            $(ev.currentTarget).find('input[type=radio]').prop('checked', true);
        }
    },

    /**
     * Resets the completion of the track so the user can take
     * the quiz again
     *
     * @private
     */
    _onClickReset: function () {
        rpc('/event_track/quiz/reset', {
            event_id: this.track.eventId,
            track_id: this.track.id
        }).then(this._resetQuiz.bind(this));
    },

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

export default Quiz;
