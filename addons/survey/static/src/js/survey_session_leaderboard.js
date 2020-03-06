odoo.define('survey.session_leaderboard', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var SESSION_CHART_COLORS = require('survey.session_colors');

publicWidget.registry.SurveySessionLeaderboard = publicWidget.Widget.extend({
    init: function (parent, options) {
        this._super.apply(this, arguments);

        this.surveyAccessToken = options.surveyAccessToken;
        this.$sessionResults = options.sessionResults;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Shows the question leaderboard on screen.
     * It's based on the attendees score (descending).
     *
     * We fade out the $sessionResults to fade in our rendered template.
     *
     * The width of the progress bars is set after the rendering to enable a width css animation.
     */
    showLeaderboard: function (fadeOut) {
        var self = this;

        var resolveFadeOut;
        var fadeOutPromise;
        if (fadeOut) {
            fadeOutPromise = new Promise(function (resolve, reject) { resolveFadeOut = resolve; });
            self.$sessionResults.fadeOut(400, function () {
                resolveFadeOut();
            });
        } else {
            fadeOutPromise = Promise.resolve();
            self.$sessionResults.hide();
            self.$('.o_survey_session_leaderboard_container').empty();
        }

        var leaderboardPromise = this._rpc({
            route: _.str.sprintf('/survey/session/leaderboard/%s', this.surveyAccessToken)
        });

        Promise.all([fadeOutPromise, leaderboardPromise]).then(function (results) {
            var leaderboardResults = results[1];
            var $renderedTemplate = $(leaderboardResults).addClass('py-3');
            self.$('.o_survey_session_leaderboard_container').append($renderedTemplate);

            self.$('.o_survey_session_leaderboard_bar').each(function (index) {
                var rgb = SESSION_CHART_COLORS[index % 10];
                $(this).css('background-color', `rgba(${rgb},${0.8})`);
            });
            self.$el.fadeIn(400, function () {
                self.$('.o_survey_session_leaderboard_bar').each(function () {
                    $(this).css('width', `calc(calc(100% - 18rem) * ${$(this).data('widthRatio')})`);
                });
            });
        });
    },

    /**
     * Inverse the process, fading out our template to fade int the $sessionResults.
     */
    hideLeaderboard: function () {
        var self = this;
        this.$el.fadeOut(400, function () {
            self.$('.o_survey_session_leaderboard_container').empty();
            self.$sessionResults.fadeIn(400);
        });
    },
});

return publicWidget.registry.SurveySessionLeaderboard;

});
