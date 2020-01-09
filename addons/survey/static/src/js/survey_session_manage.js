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
        'click .o_survey_session_refresh_results': '_onRefreshResultsClick',
        'click .o_survey_session_toggle_results': '_onToggleResultsClick',
        'click .o_survey_session_refresh_ranking': '_onRefreshRankingClick',
        'click .o_survey_session_toggle_ranking': '_onToggleRankingClick',
    },

    /**
     * Overridden to set a few properties that come from the python template rendering.
     *
     * We also handle the timer IF we're not "transitioning", meaning a fade out of the previous
     * $el to the next question.
     * If we're transitioning, the timer is handled manually at the end of the transition.
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.surveyId = self.$el.data('surveyId');
            self.surveyAccessToken = self.$el.data('surveyAccessToken');
            self.inputSessionId = self.$el.data('inputSessionId');

            var isTransitioned = self.$el.data('isTransitioned');
            if (!isTransitioned) {
                self._startTimer();
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

        var resolveFadeOut;
        var fadeOutPromise = new Promise(function (resolve, reject) { resolveFadeOut = resolve; });
        this.$el.fadeOut(1000, function () {
            resolveFadeOut();
        });

        var nextQuestionPromise = this._rpc({
            route: _.str.sprintf('/survey/session_next_question/%s', self.surveyAccessToken)
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
            model: 'survey.user_input_session',
            method: 'action_end_session',
            args: [[this.inputSessionId]],
        }).then(function () {
            document.location = _.str.sprintf(
                '/survey/results/%s/%s',
                self.surveyId,
                self.inputSessionId
            );
        });
    },

    _onToggleResultsClick: function (ev) {
        ev.preventDefault();

        if ($(ev.currentTarget).hasClass('fa-angle-double-down')) {
            this._onShowResults(ev);
        } else {
            this._onHideResults(ev);
        }
    },

    _onShowResults: function (ev) {
        var self = this;

        this.$('.o_survey_session_toggle_results')
            .removeClass('fa-angle-double-down')
            .addClass('fa-spinner fa-spin');

        this._refreshResults().then(function () {
            self.$('.o_survey_session_toggle_results')
                .removeClass('fa-spinner fa-spin')
                .addClass('fa-angle-double-up');

            self.$('.o_survey_session_refresh_results').removeClass('d-none');
        });
    },

    /**
    *
    * Hides the question results.
    * We use a height: 0 css rule to add an animation effect.
    *
    * @param {MouseEvent} ev
    * @private
    */
    _onHideResults: function (ev) {
        this.$('.o_survey_session_toggle_results')
            .removeClass('fa-angle-double-up')
            .addClass('fa-angle-double-down');

        this.$('.o_survey_session_refresh_results').addClass('d-none');

        this.$('.o_survey_result').css('height', 0);
    },

    _onRefreshResultsClick: function (ev) {
        ev.preventDefault();

        if (this.$('.o_survey_session_refresh_results').hasClass('fa-spin')) {
            return;
        }

        var refreshPromise = this._refreshResults();
        this._spinIcon(this.$('.o_survey_session_refresh_results'), refreshPromise);
    },

   _onToggleRankingClick: function (ev) {
        ev.preventDefault();

        if ($(ev.currentTarget).hasClass('fa-angle-double-down')) {
            this._onShowRanking(ev);
        } else {
            this._onHideRanking(ev);
        }
    },

   _onShowRanking: function (ev) {
        var self = this;

        this.$('.o_survey_session_toggle_ranking')
            .removeClass('fa-angle-double-down')
            .addClass('fa-spinner fa-spin');

        this._refreshRanking().then(function () {
            self.$('.o_survey_session_toggle_ranking')
                .removeClass('fa-spinner fa-spin')
                .addClass('fa-angle-double-up');

            self.$('.o_survey_session_refresh_ranking').removeClass('d-none');
        });
    },

    /**
    *
    * Hides the question ranking.
    * We use a height: 0 css rule to add an animation effect.
    *
    * @param {MouseEvent} ev
    * @private
    */
    _onHideRanking: function (ev) {
        this.$('.o_survey_session_toggle_ranking')
            .removeClass('fa-angle-double-up')
            .addClass('fa-angle-double-down');

        this.$('.o_survey_session_refresh_ranking').addClass('d-none');

        this.$('.o_survey_session_ranking_container').css('height', 0);
    },

    _onRefreshRankingClick: function (ev) {
        ev.preventDefault();

        if (this.$('.o_survey_session_refresh_ranking').hasClass('fa-spin')) {
            return;
        }

        var refreshPromise = this._refreshRanking();
        this._spinIcon(this.$('.o_survey_session_refresh_ranking'), refreshPromise);
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
     * We use a css height rule to add an animation effect after initializing the widget.
     */
    _refreshResults: function () {
        var self = this;

        return this._rpc({
            route: _.str.sprintf('/survey/session_results/%s', this.surveyAccessToken)
        }).then(function (renderedTemplate) {
            var $renderedTemplate = $(renderedTemplate).addClass('py-3');
            self.$('.o_survey_result').empty().append($renderedTemplate);
            return new publicWidget.registry.SurveyResultWidget().attachTo($renderedTemplate)
                .then(function () {
                    var newHeight = $renderedTemplate.outerHeight(true);
                    self.$('.o_survey_result').css('height', newHeight);

                    return Promise.resolve();
                });
        });
    },

    /**
     * Refreshes the question ranking on screen.
     * We use a css height rule to add an animation effect.
     */
    _refreshRanking: function () {
        var self = this;

        return this._rpc({
            route: _.str.sprintf('/survey/session_ranking/%s', this.surveyAccessToken)
        }).then(function (renderedTemplate) {
            var $renderedTemplate = $(renderedTemplate).addClass('py-3');
            self.$('.o_survey_session_ranking_container').empty().append($renderedTemplate);

            var newHeight = $renderedTemplate.outerHeight(true);
            self.$('.o_survey_session_ranking_container').css('height', newHeight);

            return Promise.resolve();
        });
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
