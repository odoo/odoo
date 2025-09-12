import { fadeIn, fadeOut } from "@survey/utils";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import SESSION_CHART_COLORS from "@survey/interactions/survey_session_colors";

export class SurveySessionLeaderboard extends Interaction {
    // Note: the class `o_survey_session_leaderboard` is present in two
    // templates: `user_input_session_manage_content` and `survey_page_statistics`.
    // This interaction is not needed in the second case. The descendant
    // combinator in the selector is used to select only the first case.
    static selector = ".o_survey_session_manage .o_survey_session_leaderboard";
    dynamicContent = {
        _root: {
            "t-on-showLeaderboard": this.showLeaderboard,
            "t-on-hideLeaderboard": this.hideLeaderboard,
        },
        ".o_survey_session_leaderboard_bar_question": {
            "t-att-style": this.getBarQuestionStyle,
        },
    };

    getBarQuestionStyle(barEl) {
        if (this.leaderboardAnimationPhase === "showQuestionScores") {
            // See also this.showQuestionScores
            return {
                transition: "width 1s ease-out",
                width: `max(calc(calc(100% - ${this.BAR_RESERVED_WIDTH_REM}rem) * ${barEl.dataset.widthRatio}), ${this.BAR_QUEST_MIN_WIDTH_REM}rem)`,
            };
        }
        return {};
    }

    setup() {
        this.fadeInOutTime = 400;
        this.BAR_QUEST_MIN_WIDTH_REM = 3.7;
        // Score width + margin + Bar score min width (css) + BAR_QUEST_MIN_WIDTH_REM + margin + nickname width
        this.BAR_RESERVED_WIDTH_REM = 6.5 + 1 + 3.7 + this.BAR_QUEST_MIN_WIDTH_REM + 1 + 7.5;
        this.BAR_HEIGHT = "3.8rem";
        this.surveyAccessToken = this.el.closest(
            ".o_survey_session_manage"
        ).dataset.surveyAccessToken;
        this.sessionResults = this.el.parentElement.querySelector(".o_survey_session_results");
    }

    /**
     * Shows the question leaderboard on screen.
     * It's based on the attendees score (descending).
     *
     * We fade out the .o_survey_session_results element to fade in our rendered template.
     *
     * The width of the progress bars is set after the rendering to enable a width css animation.
     *
     * @param {CustomEvent} ev CustomEvent triggering the function
     */
    showLeaderboard(ev) {
        let resolveFadeOut;
        let fadeOutPromise;
        const resultsEl = this.el.parentElement.querySelector(".o_survey_session_results");
        if (ev.detail.fadeOut) {
            fadeOutPromise = new Promise((resolve, reject) => {
                resolveFadeOut = resolve;
            });
            fadeOut(resultsEl, this.fadeInOutTime, () => {
                resultsEl.dispatchEvent(new CustomEvent("setDisplayNone"));
                resolveFadeOut();
            });
        } else {
            fadeOutPromise = Promise.resolve();
            resultsEl.dispatchEvent(new CustomEvent("setDisplayNone"));
            this.removeChildren(this.el.querySelector(".o_survey_session_leaderboard_container"));
        }

        const leaderboardPromise = rpc(`/survey/session/leaderboard/${this.surveyAccessToken}`);
        this.waitFor(Promise.all([fadeOutPromise, leaderboardPromise])).then(
            this.protectSyncAfterAsync((results) => {
                const leaderboardResults = results[1];
                const renderedTemplate = document.createElement("div");
                const parser = new DOMParser();
                const parsedResults = parser.parseFromString(leaderboardResults, "text/html").body
                    .firstChild;
                if (parsedResults) {
                    // In case of scored survey with no participants, parsedResults
                    // would be null and it would break the insert below
                    this.insert(parsedResults, renderedTemplate);
                }
                this.insert(
                    renderedTemplate,
                    this.el.querySelector(".o_survey_session_leaderboard_container")
                );
                this.el
                    .querySelectorAll(".o_survey_session_leaderboard_item")
                    .forEach((item, index) => {
                        const rgb = SESSION_CHART_COLORS[index % 10];
                        item.querySelector(
                            ".o_survey_session_leaderboard_bar"
                        ).style.backgroundColor = `rgba(${rgb},1)`;
                        item.querySelector(
                            ".o_survey_session_leaderboard_bar_question"
                        ).style.backgroundColor = `rgba(${rgb},0.4)`;
                    });
                fadeIn(this.el, this.fadeInOutTime, async () => {
                    if (ev.detail.isScoredQuestion) {
                        await this.waitFor(this.showQuestionScores());
                        await this.waitFor(this.sumScores());
                        await this.waitFor(this.reorderScores());
                        this.leaderboardAnimationPhase = null;
                    }
                });
            })
        );
    }

    /**
     * Inverse the process, fading out our template to fade in sessionResults.
     */
    hideLeaderboard() {
        fadeOut(this.el, this.fadeInOutTime, () => {
            this.removeChildren(this.el.querySelector(".o_survey_session_leaderboard_container"));
            fadeIn(this.sessionResults, this.fadeInOutTime);
        });
    }

    /**
     * This method animates the passed element from 0 points to {totalScore} points.
     * It will create a nice "animated" effect of a counter increasing by {increment} until it
     * reaches the actual score.
     *
     * @param {Element} scoreEl the element to animate
     * @param {Integer} currentScore the currently displayed score
     * @param {Integer} totalScore to total score to animate to
     * @param {Integer} increment the base increment of each animation iteration
     * @param {Boolean} plusSign wether or not we add a "+" before the score
     * @private
     */
    animateScoreCounter(scoreEl, currentScore, totalScore, increment, plusSign) {
        this.waitForTimeout(() => {
            const nextScore = Math.min(totalScore, currentScore + increment);
            scoreEl.textContent = `${plusSign ? "+ " : ""}${Math.round(nextScore)} p`;
            if (nextScore < totalScore) {
                this.animateScoreCounter(scoreEl, nextScore, totalScore, increment, plusSign);
            }
        }, 25);
    }

    /**
     * Helper to move a score bar from its current position in the leaderboard
     * to a new position.
     *
     * @param {Element} scoreEl the score bar to move
     * @param {Integer} position the new position in the leaderboard
     * @param {Integer} offset an offset in 'rem'
     * @param {Integer} timeout time to wait while moving before resolving the promise
     */
    animateMoveTo(scoreEl, position, offset, timeout) {
        let animationDone;
        const animationPromise = new Promise(function (resolve) {
            animationDone = resolve;
        });
        scoreEl.style.top = `calc(calc(${this.BAR_HEIGHT} * ${position}) + ${offset}rem)`;
        this.waitForTimeout(animationDone, timeout);
        return animationPromise;
    }

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
    async reorderScores() {
        let animationDone;
        const animationPromise = new Promise(function (resolve) {
            animationDone = resolve;
        });
        this.waitForTimeout(() => {
            this.leaderboardAnimationPhase = "reorderScores";
            this.el.querySelectorAll(".o_survey_session_leaderboard_item").forEach(async (item) => {
                const currentPosition = parseInt(item.dataset.currentPosition);
                const newPosition = parseInt(item.dataset.newPosition);
                if (currentPosition !== newPosition) {
                    const offset = newPosition > currentPosition ? 2 : -2;
                    await this.waitFor(this.animateMoveTo(item, newPosition, offset, 300));
                    item.style.transition = "top ease-in-out .1s";
                    await this.waitFor(this.animateMoveTo(item, newPosition, offset * -0.3, 100));
                    await this.waitFor(this.animateMoveTo(item, newPosition, 0, 0));
                    animationDone();
                }
            });
        }, 1800);
        return animationPromise;
    }

    /**
     * Will display the score for the current question.
     * We simultaneously:
     * - increase the width of "question bar"
     *   (faded out bar right next to the global score one)
     * - animate the score for the question (ex: from + 0 p to + 40 p)
     *
     * (We keep a minimum width to be able to display '+30 p' within the bar, see getBarQuestionStyle).
     *
     * @private
     */
    async showQuestionScores() {
        let animationDone;
        const animationPromise = new Promise(function (resolve) {
            animationDone = resolve;
        });
        this.waitForTimeout(() => {
            this.leaderboardAnimationPhase = "showQuestionScores";
            this.el
                .querySelectorAll(".o_survey_session_leaderboard_bar_question")
                .forEach((barEl) => {
                    const scoreEl = barEl.querySelector(
                        ".o_survey_session_leaderboard_bar_question_score"
                    );
                    scoreEl.textContent = "0 p";
                    const questionScore = parseInt(barEl.dataset.questionScore);
                    if (questionScore && questionScore > 0) {
                        let increment = parseInt(barEl.dataset.maxQuestionScore / 40);
                        if (!increment || increment === 0) {
                            increment = 1;
                        }
                        scoreEl.textContent = "+ 0 p";
                        this.waitForTimeout(() => {
                            this.animateScoreCounter(scoreEl, 0, questionScore, increment, true);
                        }, 400);
                    }
                    this.waitForTimeout(animationDone, 1400);
                });
        }, 300);
        return animationPromise;
    }

    /**
     * After displaying the score for the current question on top of the current score,
     * we update the total score on the left with an animation by summing both and fade
     * out the "+ x p" on the question score bar.
     *
     * @private
     */
    async sumScores() {
        let animationDone;
        const animationPromise = new Promise(function (resolve) {
            animationDone = resolve;
        });
        this.waitForTimeout(() => {
            this.leaderboardAnimationPhase = "sumScores";
            this.el.querySelectorAll(".o_survey_session_leaderboard_item").forEach((item) => {
                const currentScore = parseInt(item.dataset.currentScore);
                const updatedScore = parseInt(item.dataset.updatedScore);
                let increment = parseInt(item.dataset.maxQuestionScore) / 40;
                if (!increment || increment === 0) {
                    increment = 1;
                }
                this.animateScoreCounter(
                    item.querySelector(".o_survey_session_leaderboard_score"),
                    currentScore,
                    updatedScore,
                    increment,
                    false
                );
                fadeOut(
                    item.querySelector(".o_survey_session_leaderboard_bar_question_score"),
                    500
                );
                this.waitForTimeout(animationDone, 500);
            });
        }, 1400);

        return animationPromise;
    }
}

registry
    .category("public.interactions")
    .add("survey.survey_session_leaderboard", SurveySessionLeaderboard);
