/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import publicWidget from "@web/legacy/js/public/public_widget";
import SESSION_CHART_COLORS from "@survey/js/survey_session_colors";

publicWidget.registry.SurveySessionLeaderboard = publicWidget.Widget.extend({
    init: function (parent, options) {
        this._super.apply(this, arguments);

        this.surveyAccessToken = options.surveyAccessToken;
        this.$sessionResults = options.sessionResults;

        this.BAR_MIN_WIDTH = '3rem';
        this.BAR_WIDTH = '24rem';
        this.BAR_HEIGHT = '3.8rem';
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
    showLeaderboard: function (fadeOut, isScoredQuestion) {
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

        var leaderboardPromise = rpc(`/survey/session/leaderboard/${this.surveyAccessToken}`);

        Promise.all([fadeOutPromise, leaderboardPromise]).then(function (results) {
            var leaderboardResults = results[1];
            var $renderedTemplate = $(leaderboardResults);
            self.$('.o_survey_session_leaderboard_container').append($renderedTemplate);

            self.$('.o_survey_session_leaderboard_item').each(function (index) {
                var rgb = SESSION_CHART_COLORS[index % 10];
                $(this)
                    .find('.o_survey_session_leaderboard_bar')
                    .css('background-color', `rgba(${rgb},1)`);
                $(this)
                    .find('.o_survey_session_leaderboard_bar_question')
                    .css('background-color', `rgba(${rgb},${0.4})`);
            });

            self.$el.fadeIn(400, async function () {
                if (isScoredQuestion) {
                    await self._prepareScores();
                    await self._showQuestionScores();
                    await self._sumScores();
                    await self._reorderScores();
                }
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

    /**
     * This method animates the passed jQuery element from 0 points to {totalScore} points.
     * It will create a nice "animated" effect of a counter increasing by {increment} until it
     * reaches the actual score.
     *
     * @param {$.Element} $scoreEl the element to animate
     * @param {Integer} currentScore the currently displayed score
     * @param {Integer} totalScore to total score to animate to
     * @param {Integer} increment the base increment of each animation iteration
     * @param {Boolean} plusSign wether or not we add a "+" before the score
     * @private
     */
    _animateScoreCounter: function ($scoreEl, currentScore, totalScore, increment, plusSign) {
        var self = this;
        setTimeout(function () {
            var nextScore = currentScore + increment;
            if (nextScore > totalScore) {
                nextScore = totalScore;
            }
            $scoreEl.text(`${plusSign ? '+ ' : ''}${Math.round(nextScore)} p`);

            if (nextScore < totalScore) {
                self._animateScoreCounter($scoreEl, nextScore, totalScore, increment, plusSign);
            }
        }, 25);
    },

    /**
     * Helper to move a score bar from its current position in the leaderboard
     * to a new position.
     *
     * @param {$.Element} $score the score bar to move
     * @param {Integer} position the new position in the leaderboard
     * @param {Integer} offset an offset in 'rem'
     * @param {Integer} timeout time to wait while moving before resolving the promise
     */
    _animateMoveTo: function ($score, position, offset, timeout) {
        var animationDone;
        var animationPromise = new Promise(function (resolve) {
            animationDone = resolve;
        });
        $score.css('top', `calc(calc(${this.BAR_HEIGHT} * ${position}) + ${offset}rem)`);
        setTimeout(animationDone, timeout);
        return animationPromise;
    },

    /**
     * Takes the leaderboard prior to the current question results
     * and reduce all scores bars to a small width (3rem).
     * We keep the small score bars on screen for 1s.
     *
     * This visually prepares the display of points for the current question.
     *
     * @private
     */
    _prepareScores: function () {
        var self = this;
        var animationDone;
        var animationPromise = new Promise(function (resolve) {
            animationDone = resolve;
        });
        setTimeout(function () {
            this.$('.o_survey_session_leaderboard_bar').each(function () {
                var currentScore = parseInt($(this)
                    .closest('.o_survey_session_leaderboard_item')
                    .data('currentScore'))
                if (currentScore && currentScore !== 0) {
                    $(this).css('transition', `width 1s cubic-bezier(.4,0,.4,1)`);
                    $(this).css('width', self.BAR_MIN_WIDTH);
                }
            });
            setTimeout(animationDone, 1000);
        }, 300);

        return animationPromise;
    },

    /**
     * Now that we have summed the score for the current question to the total score
     * of the user and re-weighted the bars accordingly, we need to re-order everything
     * to match the new ranking.
     *
     * In addition to moving the bars to their new position, we create a "bounce" effect
     * by moving the bar a little bit more to the top or bottom (depending on if it's moving up
     * the ranking or down), the moving it the other way around, then moving it to its final
     * position.
     *
     * (Feels complicated when explained but it's fairly simple once you see what it does).
     *
     * @private
     */
    _reorderScores: function () {
        var self = this;
        var animationDone;
        var animationPromise = new Promise(function (resolve) {
            animationDone = resolve;
        });
        setTimeout(function () {
            self.$('.o_survey_session_leaderboard_item').each(async function () {
                var $score = $(this);
                var currentPosition = parseInt($(this).data('currentPosition'));
                var newPosition = parseInt($(this).data('newPosition'));
                if (currentPosition !== newPosition) {
                    var offset = newPosition > currentPosition ? 2 : -2;
                    await self._animateMoveTo($score, newPosition, offset, 300);
                    $score.css('transition', 'top ease-in-out .1s');
                    await self._animateMoveTo($score, newPosition, offset * -0.3, 100);
                    await self._animateMoveTo($score, newPosition, 0, 0);
                    animationDone();
                }
            });
        }, 1800);

        return animationPromise;
    },

    /**
     * Will display the score for the current question.
     * We simultaneously:
     * - increase the width of "question bar"
     *   (faded out bar right next to the global score one)
     * - animate the score for the question (ex: from + 0 p to + 40 p)
     *
     * (We keep a minimum width of 3rem to be able to display '+30 p' within the bar).
     *
     * @private
     */
    _showQuestionScores: function () {
        var self = this;
        var animationDone;
        var animationPromise = new Promise(function (resolve) {
            animationDone = resolve;
        });
        setTimeout(function () {
            this.$('.o_survey_session_leaderboard_bar_question').each(function () {
                var $barEl = $(this);
                var width = `calc(calc(100% - ${self.BAR_WIDTH}) * ${$barEl.data('widthRatio')} + ${self.BAR_MIN_WIDTH})`;
                $barEl.css('transition', 'width 1s ease-out');
                $barEl.css('width', width);

                var $scoreEl = $barEl
                    .find('.o_survey_session_leaderboard_bar_question_score')
                    .text('0 p');
                var questionScore = parseInt($barEl.data('questionScore'));
                if (questionScore && questionScore > 0) {
                    var increment = parseInt($barEl.data('maxQuestionScore') / 40);
                    if (!increment || increment === 0){
                        increment = 1;
                    }
                    $scoreEl.text('+ 0 p');
                    console.log($barEl.data('maxQuestionScore'));
                    setTimeout(function () {
                        self._animateScoreCounter(
                            $scoreEl,
                            0,
                            questionScore,
                            increment,
                            true);
                    }, 400);
                }
                setTimeout(animationDone, 1400);
            });
        }, 300);

        return animationPromise;
    },

    /**
     * After displaying the score for the current question, we sum the total score
     * of the user so far with the score of the current question.
     *
     * Ex:
     * We have ('#' for total score before question and '=' for current question score):
     * 210 p ####=================================== +30 p John
     * We want:
     * 240 p ###################################==== +30 p John
     *
     * Of course, we also have to weight the bars based on the maximum score.
     * So if John here has 50% of the points of the leader user, both the question score bar
     * and the total score bar need to have their width divided by 2:
     * 240 p ##################== +30 p John
     *
     * The width of both bars move at the same time to reach their new position,
     * with an animation on the width property.
     * The new width of the "question bar" should represent the ratio of won points
     * when compared to the total points.
     * (We keep a minimum width of 3rem to be able to display '+30 p' within the bar).
     *
     * The updated total score is animated towards the new value.
     * we keep this on screen for 500ms before reordering the bars.
     *
     * @private
     */
    _sumScores: function () {
        var self = this;
        var animationDone;
        var animationPromise = new Promise(function (resolve) {
            animationDone = resolve;
        });
        // values that felt the best after a lot of testing
        var growthAnimation = 'cubic-bezier(.5,0,.66,1.11)';
        setTimeout(function () {
            this.$('.o_survey_session_leaderboard_item').each(function () {
                var currentScore = parseInt($(this).data('currentScore'));
                var updatedScore = parseInt($(this).data('updatedScore'));
                var increment = parseInt($(this).data('maxQuestionScore') / 40);
                if (!increment || increment === 0){
                    increment = 1;
                }
                self._animateScoreCounter(
                    $(this).find('.o_survey_session_leaderboard_score'),
                    currentScore,
                    updatedScore,
                    increment,
                    false);

                var maxUpdatedScore = parseInt($(this).data('maxUpdatedScore'));
                var baseRatio = updatedScore / maxUpdatedScore;
                var questionScore = parseInt($(this).data('questionScore'));
                var questionRatio = questionScore /
                    (updatedScore && updatedScore !== 0 ? updatedScore : 1);
                // we keep a min fixed with of 3rem to be able to display "+ 5 p"
                // even if the user already has 1.000.000 points
                var questionWith = `calc(calc(calc(100% - ${self.BAR_WIDTH}) * ${questionRatio * baseRatio}) + ${self.BAR_MIN_WIDTH})`;
                $(this)
                    .find('.o_survey_session_leaderboard_bar_question')
                    .css('transition', `width ease .5s ${growthAnimation}`)
                    .css('width', questionWith);

                var updatedScoreRatio = 1 - questionRatio;
                var updatedScoreWidth = `calc(calc(100% - ${self.BAR_WIDTH}) * ${updatedScoreRatio * baseRatio})`;
                $(this)
                    .find('.o_survey_session_leaderboard_bar')
                    .css('min-width', '0px')
                    .css('transition', `width ease .5s ${growthAnimation}`)
                    .css('width', updatedScoreWidth);

                setTimeout(animationDone, 500);
            });
        }, 1400);

        return animationPromise;
    }
});

export default publicWidget.registry.SurveySessionLeaderboard;
