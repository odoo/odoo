import { rpc } from "@web/core/network/rpc";
import publicWidget from "@web/legacy/js/public/public_widget";
import SESSION_CHART_COLORS from "@survey/js/survey_session_colors";

publicWidget.registry.SurveySessionLeaderboard = publicWidget.Widget.extend({
    init: function (parent, options) {
        this._super.apply(this, arguments);

        this.surveyAccessToken = options.surveyAccessToken;
        this.$sessionResults = options.sessionResults;

        const BAR_QUEST_MIN_WIDTH_REM = 3.7;
        this.BAR_MIN_WIDTH = `${BAR_QUEST_MIN_WIDTH_REM}rem`;
        // Score width + margin + Bar score min width (css) + BAR_QUEST_MIN_WIDTH_REM + margin + nickname width
        this.BAR_RESERVED_WIDTH_REM = 6.5 + 1 + 3.7 + BAR_QUEST_MIN_WIDTH_REM + 1 + 7.5;
        this.BAR_WIDTH = `${this.BAR_RESERVED_WIDTH_REM}rem`;
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
        // Fix leaderboard size
        self.$el.css("min-width", `max(50vw, ${this.BAR_RESERVED_WIDTH_REM + 15}rem)`);

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
            const $container = self.$(".o_survey_session_leaderboard_container");
            $container.addClass("d-none");
            $container.append($renderedTemplate);
            self.$('.o_survey_session_leaderboard_item').each(function (index) {
                // Fix current score bar size
                const widthRatio = this.dataset.currentScore / this.dataset.maxUpdatedScore;
                const $barEl = $(this).find(".o_survey_session_leaderboard_bar");
                $barEl.css(
                    "width",
                    `calc(calc(100% - ${self.BAR_WIDTH}) * ${widthRatio})`
                );

                var rgb = SESSION_CHART_COLORS[index % 10];
                $barEl.css("background-color", `rgba(${rgb},1)`);
                $(this)
                    .find('.o_survey_session_leaderboard_bar_question')
                    .css('background-color', `rgba(${rgb},${0.4})`);
            });
            $container.removeClass("d-none");

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
     * @deprecated
     * @private
     */
    _prepareScores: function () {
        return Promise.resolve();
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
     * (We keep a minimum width of 3rem to be able to display '+30 p' within the bar through a min-width in css).
     *
     * @private
     */
    _showQuestionScores: function () {
        var self = this;
        var animationDone;
        var animationPromise = new Promise(function (resolve) {
            animationDone = resolve;
        });
        const maxUpdatedScore = this.$('.o_survey_session_leaderboard_item').data("maxUpdatedScore");
        setTimeout(function () {
            this.$('.o_survey_session_leaderboard_bar_question').each(function () {
                var $barEl = $(this);
                const widthRatio = $barEl.data("questionScore") / maxUpdatedScore;
                var width = `max(calc(calc(100% - ${self.BAR_WIDTH}) * ${widthRatio}), ${self.BAR_MIN_WIDTH})`;
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
     * After displaying the score for the current question on top of the current score,
     * we update the total score on the left with an animation by summing both and fade
     * out the "+ x p" on the question score bar.
     *
     * @private
     */
    _sumScores: function () {
        var self = this;
        var animationDone;
        var animationPromise = new Promise(function (resolve) {
            animationDone = resolve;
        });
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
                    false
                );
                $(this).find(".o_survey_session_leaderboard_bar_question_score").fadeOut(500);
            });
            setTimeout(animationDone, 500);
        }, 1400);

        return animationPromise;
    }
});

export default publicWidget.registry.SurveySessionLeaderboard;
