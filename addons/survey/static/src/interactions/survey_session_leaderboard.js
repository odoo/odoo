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
        ".o_survey_session_leaderboard_bar": {
            "t-att-style": this.getBarStyle,
        },
        ".o_survey_session_leaderboard_bar_question": {
            "t-att-style": this.getBarQuestionStyle,
        },
    };

    getBarStyle(barEl) {
        if (this.leaderboardAnimationPhase === "prepareScores") {
            // See also this.prepareScores
            const currentScore = parseInt(
                barEl.closest(".o_survey_session_leaderboard_item").dataset.currentScore
            );
            if (currentScore && currentScore !== 0) {
                return {
                    transition: "width 1s cubic-bezier(.4,0,.4,1)",
                    width: this.BAR_MIN_WIDTH,
                };
            }
        } else if (this.leaderboardAnimationPhase === "sumScores") {
            // See also this.sumScores
            const { baseRatio, questionRatio } = this.getBarRatios(barEl);
            const updatedScoreRatio = 1 - questionRatio;
            const updatedScoreWidth = `calc(calc(100% - ${this.BAR_WIDTH}) * ${
                updatedScoreRatio * baseRatio
            })`;
            return {
                transition: "width ease .5s cubic-bezier(.5,0,.66,1.11)",
                width: updatedScoreWidth,
                minWidth: "0px",
            };
        }
        return {};
    }

    getBarQuestionStyle(barEl) {
        if (this.leaderboardAnimationPhase === "showQuestionScores") {
            // See also this.showQuestionScores
            return {
                transition: "width 1s ease-out",
                width: `calc(calc(100% - ${this.BAR_WIDTH}) * ${barEl.dataset.widthRatio} + ${this.BAR_MIN_WIDTH})`,
            };
        } else if (this.leaderboardAnimationPhase === "sumScores") {
            // See also this.sumScores
            const { baseRatio, questionRatio } = this.getBarRatios(barEl);
            // we keep a min fixed width of 3rem to be able to display "+ 5 p"
            // even if the user already has 1,000,000 points
            const questionWidth = `calc(calc(calc(100% - ${this.BAR_WIDTH}) * ${
                questionRatio * baseRatio
            }) + ${this.BAR_MIN_WIDTH})`;
            return {
                transition: "width ease .5s cubic-bezier(.5,0,.66,1.11)",
                width: questionWidth,
            };
        }
        return {};
    }

    getBarRatios(barEl) {
        const item = barEl.closest(".o_survey_session_leaderboard_item");
        const updatedScore = parseInt(item.dataset.updatedScore);
        const questionScore = parseInt(item.dataset.questionScore);
        const maxUpdatedScore = parseInt(item.dataset.maxUpdatedScore);
        const baseRatio = maxUpdatedScore ? updatedScore / maxUpdatedScore : 1;
        const questionRatio = questionScore / (updatedScore || 1);
        return { baseRatio, questionRatio };
    }

    setup() {
        this.fadeInOutTime = 400;
        this.BAR_MIN_WIDTH = "3rem";
        this.BAR_WIDTH = "24rem";
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
                        await this.waitFor(this.prepareScores());
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
     * Takes the leaderboard prior to the current question results
     * and reduce all scores bars to a small width (3rem).
     * We keep the small score bars on screen for 1s.
     *
     * This visually prepares the display of points for the current question.
     *
     * @private
     */
    async prepareScores() {
        let animationDone;
        const animationPromise = new Promise(function (resolve) {
            animationDone = resolve;
        });
        this.waitForTimeout(() => {
            this.leaderboardAnimationPhase = "prepareScores";
            this.waitForTimeout(animationDone, 1000);
        }, 300);
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
     * (We keep a minimum width of 3rem to be able to display '+30 p' within the bar).
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
                let increment = parseInt(item.dataset.maxQuestionScore / 40);
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
                this.waitForTimeout(animationDone, 500);
            });
        }, 1400);

        return animationPromise;
    }
}

registry
    .category("public.interactions")
    .add("survey.survey_session_leaderboard", SurveySessionLeaderboard);
