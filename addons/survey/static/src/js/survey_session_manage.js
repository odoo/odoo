odoo.define('survey.session_manage', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var core = require('web.core');
var _t = core._t;

publicWidget.registry.SurveySessionManage = publicWidget.Widget.extend({
    selector: '.o_survey_session_manage',
    events: {
        'click .o_survey_session_copy': '_onCopySessionLink',
        'click .o_survey_session_next, .o_survey_session_start': '_onNextQuestionClick',
        'click .o_survey_session_end': '_onEndSessionClick',
        'click .o_survey_session_results_href': '_onResultsTabClick',
        'click .o_survey_session_ranking_href': '_onRankingTabClick',
        'click .o_survey_session_refresh_results': '_onRefreshResultsClick',
        'click .o_survey_session_refresh_ranking': '_onRefreshRankingClick',
    },

    /**
     * Overridden to set a few properties that come from the python template rendering.
     *
     * We also handle the timer IF we're not "transitioning", meaning a fade out of the previous
     * $el to the next question (the fact that we're transitioning is in the isRpcCall data).
     * If we're transitioning, the timer is handled manually at the end of the transition.
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.surveyId = self.$el.data('surveyId');
            self.surveyAccessToken = self.$el.data('surveyAccessToken');
            self.isStartScreen = self.$el.data('isStartScreen');

            var isRpcCall = self.$el.data('isRpcCall');
            if (!isRpcCall) {
                self._startTimer();
            }

            if (self.isStartScreen) {
                self._refreshAttendeesCount();
            } else if (!self.refreshingAnswers) {
                self.stopRefreshingAttendees = true;
                self._refreshReceivedAnswers();
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Copies the survey URL link to the clipboard.
     * We use 'ClipboardJS' to avoid having to print the URL in a standard text input
     *
     * @param {MouseEvent} ev
     */
    _onCopySessionLink: function (ev) {
        var self = this;
        ev.preventDefault();

        var $clipboardBtn = this.$('.o_survey_session_copy');

        $clipboardBtn.popover({
            placement: 'right',
            container: 'body',
            offset: '0, 3',
            content: function () {
                return _t("Copied !");
            }
        });

        var clipboard = new ClipboardJS('.o_survey_session_copy', {
            text: function () {
                return self.$('.o_survey_session_copy_url').val();
            },
            container: this.el
        });

        clipboard.on('success', function () {
            clipboard.destroy();
            $clipboardBtn.popover('show');
            _.delay(function () {
                $clipboardBtn.popover('hide');
            }, 800);
        });

        clipboard.on('error', function (e) {
            clipboard.destroy();
        });
    },

    /**
    * We use a fade in/out mechanism to display the next question of the session.
    *
    * The fade out happens at the same moment as the _rpc to get the new question template.
    * When they're both finished, we update the HTML of this widget with the new template and then
    * fade in the updated question to the user.
    *
    * The timer (if configured) starts at the end of the fade in animation.
    *
    * @param {MouseEvent} ev
    * @private
    */
    _onNextQuestionClick: function (ev) {
        var self = this;
        ev.preventDefault();
        this.isStartScreen = false;

        var resolveFadeOut;
        var fadeOutPromise = new Promise(function (resolve, reject) { resolveFadeOut = resolve; });
        this.$el.fadeOut(1000, function () {
            resolveFadeOut();
        });

        var nextQuestionPromise = this._rpc({
            route: _.str.sprintf('/survey/session/next_question/%s', self.surveyAccessToken)
        });

        Promise.all([fadeOutPromise, nextQuestionPromise]).then(function (results) {
            var $renderedTemplate = $(results[1]);
            self.$el.replaceWith($renderedTemplate);
            self.attachTo($renderedTemplate);
            self.$el.fadeIn(1000, function () {
                self._startTimer();
            });
        });
    },

    /**
    * Marks this session as 'done' and redirects the user to the results.
    *
    * @param {MouseEvent} ev
    * @private
    */
   _onEndSessionClick: function (ev) {
        var self = this;
        ev.preventDefault();

        this._rpc({
            model: 'survey.survey',
            method: 'action_end_session',
            args: [[this.surveyId]],
        }).then(function () {
            document.location = _.str.sprintf(
                '/survey/results/%s',
                self.surveyId
            );
        });
    },

    _onResultsTabClick: function (ev) {
        this._onRefreshResultsClick(ev, true);
    },

    _onRankingTabClick: function (ev) {
        this._onRefreshRankingClick(ev, true);
    },

    _onRefreshResultsClick: function (ev, preventSpin) {
        ev.preventDefault();

        if (this.$('.o_survey_session_refresh_results').hasClass('fa-spin')) {
            return;
        }

        var refreshPromise = this._refreshResults();
        if (!preventSpin) {
            this._spinIcon(this.$('.o_survey_session_refresh_results'), refreshPromise);
        }
    },

    _onRefreshRankingClick: function (ev, preventSpin) {
        ev.preventDefault();

        if (this.$('.o_survey_session_refresh_ranking').hasClass('fa-spin')) {
            return;
        }

        var refreshPromise = this._refreshRanking();

        if (!preventSpin) {
            this._spinIcon(this.$('.o_survey_session_refresh_ranking'), refreshPromise);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Will start the question timer so that the host may know when the question is done to display
     * the results and the ranking.
     */
    _startTimer: function () {
        var $timer = this.$('.o_survey_timer');

        if ($timer.length) {
            var timeLimitMinutes = this.$el.data('timeLimitMinutes');
            var timer = this.$el.data('timer');
            this.surveyTimerWidget = new publicWidget.registry.SurveyTimerWidget(this, {
                'timer': timer,
                'timeLimitMinutes': timeLimitMinutes
            });
            this.surveyTimerWidget.attachTo($timer);
        }
    },

    /**
     * Refreshes the question results on screen.
     */
    _refreshResults: function () {
        var self = this;

        return this._rpc({
            route: _.str.sprintf('/survey/session/results/%s', this.surveyAccessToken)
        }).then(function (renderedTemplate) {
            var $renderedTemplate = $(renderedTemplate).addClass('py-3');
            self.$('.o_survey_result').empty().append($renderedTemplate);
            return new publicWidget.registry.SurveyResultWidget().attachTo($renderedTemplate);
        });
    },

    /**
     * Refreshes the question ranking on screen.
     * We set the width of the progress bars after the rendering to enable a width css animation.
     */
    _refreshRanking: function () {
        var self = this;

        return this._rpc({
            route: _.str.sprintf('/survey/session/ranking/%s', this.surveyAccessToken)
        }).then(function (renderedTemplate) {
            var $renderedTemplate = $(renderedTemplate).addClass('py-3');
            self.$('.o_survey_session_ranking_container').empty().append($renderedTemplate);
            // delay by 200ms to account for fade out / in
            setTimeout(function () {
                self.$('.o_survey_session_ranking_bar').each(function () {
                    $(this).css('width', `calc(calc(100% - 10rem) * ${$(this).data('widthRatio')})`);
                });
            }, 200);

            return Promise.resolve();
        });
    },

    /**
     * We refresh the attendees count every 2 seconds while the user is on the start screen.
     * When he leaves the start screen, the "stopRefreshingAttendees" becomes true and we stop
     * querying the answer_count.
     */
    _refreshAttendeesCount: function () {
        var self = this;

        setTimeout(function () {
            self._rpc({
                model: 'survey.survey',
                method: 'read',
                args: [[self.surveyId], ['answer_count']],
            }).then(function (result) {
                if (result && result.length === 1){
                    self.$('.o_survey_session_attendees_count').text(
                        result[0].answer_count
                    );
                }
                if (!self.stopRefreshingAttendees) {
                    self._refreshAttendeesCount();
                }
            });
        }, 2000);
    },

    /**
     * We refresh the received answers count every 2 seconds for the current question.
     * This allows the host to know what he can move on to the next question.
     * (Without having to manually refresh the page).
     */
    _refreshReceivedAnswers: function () {
        var self = this;

        this.refreshingAnswers = true;
        setTimeout(function () {
            self._rpc({
                model: 'survey.survey',
                method: 'read',
                args: [[self.surveyId], ['session_question_answer_count']],
            }).then(function (result) {
                if (result && result.length === 1){
                    self.$('.o_survey_session_answer_count').text(
                        result[0].session_question_answer_count
                    );
                }
                self._refreshReceivedAnswers();
            });
        }, 2000);
    },

    /**
     * We need the refresh icon to spin for at least 1s to make the user feel like it's
     * refreshing something.
     * If we only wait for the 'refreshPromise', it can be so fast that the icon doesn't even move.
     *
     * @param {$.Element} $target
     * @param {Promise} refreshPromise
     */
    _spinIcon: function ($target, refreshPromise) {
        $target.addClass('fa-spin');

        var minimumSpinResolve;
        var minimumSpinPromise = new Promise(function (resolve) { minimumSpinResolve = resolve;});
        setTimeout(function () {
            minimumSpinResolve();
        }, 1000);

        Promise.all([minimumSpinPromise, refreshPromise]).then(function () {
            $target.removeClass('fa-spin');
        });
    },
});

return publicWidget.registry.SurveySessionManage;

});
