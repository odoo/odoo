import { preloadBackground } from "@survey/js/survey_preload_image_mixin";
import publicWidget from "@web/legacy/js/public/public_widget";
import SurveySessionChart from "@survey/interactions/survey_session_chart";
import SurveySessionTextAnswers from "@survey/interactions/survey_session_text_answers";
import SurveySessionLeaderBoard from "@survey/interactions/survey_session_leaderboard";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { browser } from "@web/core/browser/browser";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { fadeInEffect, fadeOutEffect } from "./fade_in_out_effects";

const nextPageTooltips = {
    closingWords: _t("End of Survey"),
    leaderboard: _t("Show Leaderboard"),
    leaderboardFinal: _t("Show Final Leaderboard"),
    nextQuestion: _t("Next"),
    results: _t("Show Correct Answer(s)"),
    startScreen: _t("Start"),
    userInputs: _t("Show Results"),
};

export class SurveySessionManage extends Interaction {
    static selector = ".o_survey_session_manage";

    dynamicContent = {
        ".o_survey_session_copy": {
            "t-on-click.prevent": this.onCopySessionLink,
        },
        ".o_survey_session_navigation_next": {
            "t-on-click.prevent": this.onNext,
        },
        ".o_survey_session_navigation_previous": {
            "t-on-click.prevent": this.onBack,
            "t-att-class": () => ({ "d-none": !!this.isFirstQuestion }),
        },
        ".o_survey_session_close": {
            "t-on-click.prevent": this.onEndSessionClick,
        },
        ".o_survey_session_attendees_count": {
            "t-out": () => this.sessionAttendeesCountText,
        },
        ".o_survey_session_navigation_next_label": {
            "t-out": () => this.sessionNavigationNextLabel,
        },
    };

    /**
     * TODO: refactor when the three widgets will be converted
     */
    async willStart() {
        const setupPromises = [];
        setupPromises.push(this._setupTextAnswers());
        setupPromises.push(this._setupChart());
        setupPromises.push(this._setupLeaderboard());
        await Promise.all(setupPromises);
    }

    setup() {
        this.fadeInOutTime = 500;
        if (this.el.dataset["isSessionClosed"]) {
            this.displaySessionClosedPage();
            this.el.classList.remove("invisible");
            return;
        }
        // general survey props
        this.surveyId = parseInt(this.el.dataset["surveyId"]);
        this.surveyHasConditionalQuestions = this.el.dataset["surveyHasConditionalQuestions"];
        this.surveyAccessToken = this.el.dataset["surveyAccessToken"];
        this.isStartScreen = this.el.dataset["isStartScreen"];
        this.isFirstQuestion = this.el.dataset["isFirstQuestion"];
        this.isLastQuestion = this.el.dataset["isLastQuestion"];
        this.surveyLastTriggeringAnswers = JSON.parse(
            this.el.dataset["surveyLastTriggeringAnswers"] || "[]"
        );
        // scoring props
        this.isScoredQuestion = this.el.dataset["isScoredQuestion"];
        this.sessionShowLeaderboard = this.el.dataset["sessionShowLeaderboard"];
        this.hasCorrectAnswers = this.el.dataset["hasCorrectAnswers"];
        // display props
        this.showBarChart = this.el.dataset["showBarChart"];
        this.showTextAnswers = this.el.dataset["showTextAnswers"];
        // Question transition
        this.stopNextQuestion = false;
        // Background Management
        this.refreshBackground = this.el.dataset["refreshBackground"];
        // Copy link tooltip
        this.copyBtnTooltip = window.Tooltip.getOrCreateInstance(
            this.el.querySelector(".o_survey_session_copy"),
            {
                title: _t("Click to copy link"),
                placement: "right",
                container: "body",
                trigger: "hover",
                offset: "0, 3",
                delay: 0,
            }
        );
        this.registerCleanup(() => this.copyBtnTooltip?.dispose());

        // We handle the timer IF we're not "transitioning", meaning a fade out
        // of the previous question screen to the next question (the fact that
        // we're transitioning is in the isRpcCall data). If we're transitioning,
        // the timer is handled manually at the end of the transition.
        const isRpcCall = this.el.dataset["isRpcCall"];
        if (!isRpcCall) {
            this.startTimer();
        }

        this.sessionAttendeesCountText = "";
        this.sessionNavigationNextLabel = "";

        this.el.classList.remove("invisible");

        this.setupIntervals();
    }

    start() {
        // Check if the page is being loaded as a result of going back
        if (this.el.dataset["goingBack"]) {
            this.setShowInputs(true);
            this.setShowAnswers(true);
            if (this.sessionShowLeaderboard && this.isScoredQuestion) {
                this.currentScreen = "leaderboard";
                this.leaderBoard.showLeaderboard(false, this.isScoredQuestion);
            } else {
                this.currentScreen = "results";
                this.refreshResults();
            }
        }
        this.setupCurrentScreen();
        this.addListener(document, "keydown", this.onKeyDown.bind(this));
    }
    /**
     * Copies the survey URL link to the clipboard.
     * We avoid having to print the URL in a standard text input.
     *
     * @param {MouseEvent} ev
     */
    async onCopySessionLink(ev) {
        this.copyBtnTooltip?.dispose();
        delete this.copyBtnTooltip;
        const copyBtnPopover = window.Popover.getOrCreateInstance(ev.currentTarget, {
            content: _t("Copied!"),
            trigger: "manual",
            placement: "right",
            container: "body",
            offset: "0, 3",
        });
        this.registerCleanup(() => copyBtnPopover.dispose());
        this.waitFor(
            browser.navigator.clipboard.writeText(
                ev.currentTarget.classList.contains("o_survey_session_copy_url")
                    ? ev.currentTarget.textContent
                    : ev.currentTarget.querySelector(".o_survey_session_copy_url").textContent
            )
        ).then(
            this.protectSyncAfterAsync(() => {
                copyBtnPopover.show();
                this.waitForTimeout(() => copyBtnPopover.hide(), 800);
            })
        );
    }

    /**
     * Handles the "next screen" behavior.
     * It happens when the host uses the keyboard key / button to go to the next screen.
     * The result depends on the current screen we're on.
     *
     * Possible values of the "next screen" to display are:
     * - 'userInputs' when going from a question to the display of attendees' survey.user_input.line
     *   for that question.
     * - 'results' when going from the inputs to the actual correct / incorrect answers of that
     *   question. Only used for scored simple / multiple choice questions.
     * - 'leaderboard' (or 'leaderboardFinal') when going from the correct answers of a question to
     *   the leaderboard of attendees. Only used for scored simple / multiple choice questions.
     * - If it's not one of the above: we go to the next question, or end the session if we're on
     *   the last question of this session.
     *
     * See 'getNextScreen' for a detailed logic.
     *
     * @param {Event} ev
     */
    onNext(ev) {
        const screenToDisplay = this.getNextScreen();
        switch (screenToDisplay) {
            case "userInputs":
                this.setShowInputs(true);
                break;
            case "results":
                this.setShowAnswers(true);
                // when showing results, stop refreshing answers
                clearInterval(this.resultsRefreshInterval);
                delete this.resultsRefreshInterval;
                break;
            case "leaderboard":
            case "leaderboardFinal":
                if (!["leaderboard", "leaderboardFinal"].includes(this.currentScreen)) {
                    if (this.isLastQuestion) {
                        this.el
                            .querySelector(".o_survey_session_navigation_next")
                            .classList.add("d-none");
                    }
                    // TODO reactivate fadeout after refactoring leaderboard
                    this.leaderBoard.showLeaderboard(false, this.isScoredQuestion);
                }
                break;
            default:
                if (!this.isLastQuestion || !this.sessionShowLeaderboard) {
                    this.goToNextQuestion();
                }
                break;
        }
        this.currentScreen = screenToDisplay;
        // To avoid a flicker, we do not update the tooltip when going to the next question,
        // as it will be done in "_setupCurrentScreen"
        if (!["question", "nextQuestion"].includes(screenToDisplay)) {
            this.updateNextScreenTooltip();
        }
    }

    /**
     * Reverse behavior of 'onNext'.
     *
     * @param {Event} ev
     */
    onBack(ev) {
        const screenToDisplay = this.getPreviousScreen();
        switch (screenToDisplay) {
            case "question":
                this.setShowInputs(false);
                break;
            case "userInputs":
                this.setShowAnswers(false);
                // resume refreshing answers if necessary
                if (!this.resultsRefreshInterval) {
                    this.resultsRefreshInterval = setInterval(this.refreshResults.bind(this), 2000);
                }
                break;
            case "results":
                if (this.leaderBoard) {
                    this.leaderBoard.hideLeaderboard();
                }
                // when showing results, stop refreshing answers
                clearInterval(this.resultsRefreshInterval);
                delete this.resultsRefreshInterval;
                break;
            case "previousQuestion":
                if (this.isFirstQuestion) {
                    return; // nothing to go back to, we're on the first question
                }
                this.goToNextQuestion(true);
                break;
        }
        this.currentScreen = screenToDisplay;
        // To avoid a flicker, we do not update the tooltip when going to the next question,
        // as it will be done in "_setupCurrentScreen"
        if (!["question", "nextQuestion"].includes(screenToDisplay)) {
            this.updateNextScreenTooltip();
        }
    }

    /*
     * Business logic that determines the 'next screen' based on the current screen and the question
     * configuration.
     *
     * Breakdown of use cases:
     * - If we're on the 'question' screen, and the question is scored, we move to the 'userInputs'
     * - If we're on the 'question' screen and it's NOT scored, then we move to
     *     - 'results' if the question has correct / incorrect answers
     *       (but not scored, which is kind of a corner case)
     *     - 'nextQuestion' otherwise
     * - If we're on the 'userInputs' screen and the question has answers, we move to the 'results'
     * - If we're on the 'results' and the question is scored, we move to the 'leaderboard'
     * - In all other cases, we show the next question
     * - (Small exception for the last question: we show the "final leaderboard")
     *
     * (For details about which screen shows what, see '_onNext')
     */
    getNextScreen() {
        if (this.currentScreen === "question" && this.isScoredQuestion) {
            return "userInputs";
        } else if (
            this.hasCorrectAnswers &&
            ["question", "userInputs"].includes(this.currentScreen)
        ) {
            return "results";
        } else if (this.sessionShowLeaderboard) {
            if (
                ["question", "userInputs", "results"].includes(this.currentScreen) &&
                this.isScoredQuestion
            ) {
                return "leaderboard";
            } else if (this.isLastQuestion) {
                return "leaderboardFinal";
            }
        }
        return "nextQuestion";
    }

    /**
     * Reverse behavior of 'getNextScreen'.
     *
     * @param {Event} ev
     */
    getPreviousScreen() {
        if (this.currentScreen === "userInputs" && this.isScoredQuestion) {
            return "question";
        } else if (
            (this.currentScreen === "results" && this.isScoredQuestion) ||
            (this.currentScreen === "leaderboard" && !this.isScoredQuestion) ||
            (this.currentScreen === "leaderboardFinal" && this.isScoredQuestion)
        ) {
            return "userInputs";
        } else if (
            (this.currentScreen === "leaderboard" && this.isScoredQuestion) ||
            (this.currentScreen === "leaderboardFinal" && !this.isScoredQuestion)
        ) {
            return "results";
        }
        return "previousQuestion";
    }

    /**
     * We use a fade in/out mechanism to display the next question of the session.
     *
     * The fade out happens at the same moment as the RPC to get the new question
     * template. When they're both finished, we update the HTML of this interaction
     * with the new template and then fade in the updated question to the user.
     *
     * The timer (if configured) starts at the end of the fade in animation.
     *
     * @param {MouseEvent} ev
     * @private
     */
    async goToNextQuestion(goBack) {
        // The following lines prevent calling multiple times "get next question"
        // process until next question is fully loaded.
        if (this.stopNextQuestion) {
            return;
        }
        this.stopNextQuestion = true;

        this.isStartScreen = false;
        if (this.surveyTimerWidget) {
            this.surveyTimerWidget.destroy();
        }

        let resolveFadeOut;
        const fadeOutPromise = new Promise(function (resolve, reject) {
            resolveFadeOut = resolve;
        });
        fadeOutEffect(this.el, this.fadeInOutTime, function () {
            resolveFadeOut();
        });

        if (this.refreshBackground) {
            document
                .querySelector("div.o_survey_background")
                .classList.add("o_survey_background_transition");
        }

        // avoid refreshing results while transitioning
        if (this.resultsRefreshInterval) {
            clearInterval(this.resultsRefreshInterval);
            delete this.resultsRefreshInterval;
        }
        const nextQuestionPromise = rpc(`/survey/session/next_question/${this.surveyAccessToken}`, {
            go_back: goBack,
        }).then((result) => {
            this.nextQuestion = result;
            if (this.refreshBackground && result.background_image_url) {
                return preloadBackground(result.background_image_url);
            } else {
                return Promise.resolve();
            }
        });
        await this.waitFor(Promise.all([fadeOutPromise, nextQuestionPromise]));
        this.protectSyncAfterAsync(() => this.onNextQuestionDone(goBack))();
    }

    /**
     * Refresh the screen with the next question's rendered template.
     *
     * @param {boolean} goBack Whether we are going back to the previous question or not
     */
    async onNextQuestionDone(goBack) {
        if (!this.nextQuestion.question_html) {
            this.el.querySelector(".o_survey_session_close").click();
            this.displaySessionClosedPage();
            return;
        }
        const newContentDiv = document.createElement("div");
        newContentDiv.innerHTML = this.nextQuestion.question_html;
        const newContent = newContentDiv.firstElementChild;
        newContent.style.opacity = 0;
        this.el.parentNode.replaceChild(newContent, this.el);

        if (goBack) {
            // If the question is loaded with goBack flag, we need to start
            // from the leaderboard screen. This is achieved by adding a
            // data-going-back attribute to the newContentChild
            newContent.dataset["goingBack"] = true;
        } else {
            this.startTimer();
        }

        // Background Management
        if (this.refreshBackground) {
            const surveyBackground = newContent.querySelector("div.o_survey_background");
            if (surveyBackground) {
                surveyBackground.style.backgroundImage = `url(${this.nextQuestion.background_image_url})`;
                surveyBackground.classList.remove("o_survey_background_transition");
            }
        }

        // Fade in the new content, wait for the interactions to be ready and then
        // stop the interaction on the old content (the one execuing this code)
        fadeInEffect(newContent, this.fadeInOutTime);
        await this.services["public.interactions"].startInteractions(newContent);
        this.services["public.interactions"].stopInteractions(this.el);
    }

    /**
     * Marks this session as 'done' and redirects the user to the results based on the clicked link.
     *
     * @param {MouseEvent} ev
     * @private
     */
    async onEndSessionClick(ev) {
        const currentTarget = ev.currentTarget;
        await this.waitFor(
            this.services.orm.call("survey.survey", "action_end_session", [[this.surveyId]])
        );
        this.protectSyncAfterAsync(() => {
            if (currentTarget.dataset["showResults"]) {
                window.location.href = `/survey/results/${encodeURIComponent(this.surveyId)}`;
            } else {
                window.location.reload();
            }
        })();
    }

    /**
     * Listeners for keyboard arrow / spacebar keys.
     *
     * @param {KeyboardEvent} ev
     */
    onKeyDown(ev) {
        if (ev.key === "ArrowRight" || ev.key === " ") {
            this.onNext(ev);
        } else if (ev.key === "ArrowLeft") {
            this.onBack(ev);
        }
    }

    /**
     * Setup current screen based on question properties.
     * If it's a non-scored question with a chart, we directly display the user inputs.
     */
    setupCurrentScreen() {
        if (this.isStartScreen) {
            this.currentScreen = "startScreen";
        } else if (!this.isScoredQuestion && this.showBarChart) {
            this.currentScreen = "userInputs";
        } else {
            this.currentScreen = "question";
        }
        this.setShowInputs(this.currentScreen === "userInputs");
        this.updateNextScreenTooltip();
    }

    /**
     * When we go from the 'question' screen to the 'userInputs' screen, we toggle this boolean
     * and send the information to the chart.
     * The chart will show attendees survey.user_input.lines.
     * TODO: refactor when converting SurveySessionChart widget
     * @param {Boolean} showInputs
     */
    setShowInputs(showInputs) {
        if (this.resultsChart) {
            this.resultsChart.setShowInputs(showInputs);
            this.resultsChart.updateChart();
        }
    }

    /**
     * When we go from the 'userInputs' screen to the 'results' screen, we toggle this boolean
     * and send the information to the chart.
     * The chart will show the question survey.question.answers.
     * (Only used for simple / multiple choice questions).
     * TODO: refactor when converting SurveySessionChart widget
     * @param {Boolean} showAnswers
     */
    setShowAnswers(showAnswers) {
        if (this.resultsChart) {
            this.resultsChart.setShowAnswers(showAnswers);
            this.resultsChart.updateChart();
        }
    }

    /**
     * Updates the tooltip for current page (on right arrow icon for 'Next' content).
     * this method will be called on Clicking of Next and Previous Arrow to show the
     * tooltip for the Next Content.
     */
    updateNextScreenTooltip() {
        let tooltip;
        if (this.currentScreen === "startScreen") {
            tooltip = nextPageTooltips["startScreen"];
        } else if (
            this.isLastQuestion &&
            !this.surveyHasConditionalQuestions &&
            !this.isScoredQuestion &&
            !this.sessionShowLeaderboard
        ) {
            tooltip = nextPageTooltips["closingWords"];
        } else {
            const nextScreen = this.getNextScreen();
            if (nextScreen === "nextQuestion" || this.surveyHasConditionalQuestions) {
                tooltip = nextPageTooltips["nextQuestion"];
            }
            tooltip = nextPageTooltips[nextScreen];
        }
        const sessionNavigationNextEl = this.el.querySelector(
            ".o_survey_session_navigation_next_label"
        );
        if (sessionNavigationNextEl && tooltip) {
            this.sessionNavigationNextLabel = tooltip;
            this.updateContent();
        }
    }

    /**
     * For simple/multiple choice questions, we display a bar chart with:
     *
     * - answers of attendees
     * - correct / incorrect answers when relevant
     *
     * see SurveySessionChart widget doc for more information.
     * TODO: refactor when converting SurveySessionChart widget
     */
    _setupChart() {
        if (this.resultsChart) {
            this.resultsChart.setElement(null);
            this.resultsChart.destroy();
            delete this.resultsChart;
        }

        if (!this.isStartScreen && this.showBarChart) {
            this.resultsChart = new SurveySessionChart(this, {
                questionType: this.el.dataset["questionType"],
                answersValidity: this.el.dataset["answersValidity"],
                hasCorrectAnswers: this.hasCorrectAnswers,
                questionStatistics: JSON.parse(this.el.dataset["questionStatistics"]),
                showInputs: this.showInputs,
            });

            return this.resultsChart.attachTo(this.el.querySelector(".o_survey_session_chart"));
        } else {
            return Promise.resolve();
        }
    }

    /**
     * Leaderboard of all the attendees based on their score.
     * see SurveySessionLeaderBoard widget doc for more information.
     * TODO: refactor when converting SurveySessionLeaderBoard widget
     */
    _setupLeaderboard() {
        if (this.leaderBoard) {
            this.leaderBoard.setElement(null);
            this.leaderBoard.destroy();
            delete this.leaderBoard;
        }
        if (this.isScoredQuestion || this.isLastQuestion) {
            this.leaderBoard = new SurveySessionLeaderBoard(this, {
                surveyAccessToken: this.surveyAccessToken,
                sessionResults: this.el.querySelector(".o_survey_session_results"),
            });

            return this.leaderBoard.attachTo(
                this.el.querySelector(".o_survey_session_leaderboard")
            );
        } else {
            return Promise.resolve();
        }
    }

    /**
     * Shows attendees answers for char_box/date and datetime questions.
     * see SurveySessionTextAnswers widget doc for more information.
     * TODO: refactor when converting SurveySessionTextAnswers widget
     */
    _setupTextAnswers() {
        if (this.textAnswers) {
            this.textAnswers.setElement(null);
            this.textAnswers.destroy();
            delete this.textAnswers;
        }

        if (!this.isStartScreen && this.showTextAnswers) {
            this.textAnswers = new SurveySessionTextAnswers(this, {
                questionType: this.el.dataset["questionType"],
            });

            return this.textAnswers.attachTo(
                this.el.querySelector(".o_survey_session_text_answers_container")
            );
        } else {
            return Promise.resolve();
        }
    }

    /**
     * Setup the 2 refresh intervals of 2 seconds for our widget:
     * - The refresh of attendees count (only on the start screen)
     * - The refresh of results (used for chart/text answers/progress bar)
     */
    setupIntervals() {
        this.attendeesCount = this.el.dataset["attendeesCount"]
            ? parseInt(this.el.dataset["attendeesCount"], 10)
            : 0;
        if (this.isStartScreen) {
            this.attendeesRefreshInterval = setInterval(
                this.refreshAttendeesCount.bind(this),
                2000
            );
        } else {
            if (this.attendeesRefreshInterval) {
                clearInterval(this.attendeesRefreshInterval);
            }
            if (!this.resultsRefreshInterval) {
                this.resultsRefreshInterval = setInterval(this.refreshResults.bind(this), 2000);
            }
        }
    }

    displaySessionClosedPage() {
        this.el.querySelector(".o_survey_question_header")?.classList.add("invisible");
        const elementsToHide = this.el.querySelectorAll(
            ".o_survey_session_results, .o_survey_session_navigation_previous, .o_survey_session_navigation_next"
        );
        for (const element of elementsToHide) {
            element.classList.add("d-none");
        }
        this.el.querySelector(".o_survey_session_description_done").classList.remove("d-none");
    }

    /**
     * Will start the question timer so that the host may know when the question is done to display
     * the results and the leaderboard.
     *
     * If the question is scored, the timer ending triggers the display of attendees inputs.
     * TODO: refactor when SurveyTimerWidget is converted
     *       surveyTimerWidget was triggering up a "time_up" signal
     *       to simulate a click on "o_survey_session_navigation_next".
     *       This functionality is currently missing (see commented lines)
     */
    startTimer() {
        const timerEl = this.el.querySelector(".o_survey_timer");
        if (timerEl) {
            const timeLimitMinutes = this.el.dataset["timeLimitMinutes"];
            const timer = this.el.dataset["timer"];
            this.surveyTimerWidget = new publicWidget.registry.SurveyTimerWidget(this, {
                timer: timer,
                timeLimitMinutes: timeLimitMinutes,
            });
            this.surveyTimerWidget.attachTo(timerEl);
            // this.surveyTimerWidget.on('time_up', this, function () {
            //     if (self.currentScreen === 'question' && this.isScoredQuestion) {
            //         self.$('.o_survey_session_navigation_next').click();
            //     }
            // });
        }
    }

    // TODO: remove once SurveyTimerWidget is converted
    _trigger_up() {}

    /**
     * Refreshes the question results.
     *
     * What we get from this call:
     * - The 'question statistics' used to display the bar chart when appropriate
     * - The 'user input lines' that are used to display text/date/datetime answers on the screen
     * - The number of answers, useful for refreshing the progress bar
     */
    refreshResults() {
        this.waitFor(rpc(`/survey/session/results/${this.surveyAccessToken}`)).then(
            this.protectSyncAfterAsync((questionResults) => {
                if (questionResults) {
                    this.attendeesCount = questionResults.attendees_count;

                    if (this.resultsChart && questionResults.question_statistics_graph) {
                        const parsedStatistics = JSON.parse(
                            questionResults.question_statistics_graph
                        );
                        if (parsedStatistics.length > 0) {
                            this.resultsChart.updateChart(parsedStatistics);
                        }
                    } else if (this.textAnswers) {
                        this.textAnswers.updateTextAnswers(questionResults.input_line_values);
                    }

                    // Update the last question next screen tooltip depending on the selected answers.
                    // Because if a selected answer triggers a conditional question, the last question
                    // may no longer be the last (see PR odoo/odoo#212890).
                    if (this.surveyLastTriggeringAnswers.length) {
                        this.isLastQuestion =
                            !questionResults.answer_count ||
                            !this.surveyLastTriggeringAnswers.some((answerId) =>
                                questionResults.selected_answers.includes(answerId)
                            );
                        this.updateNextScreenTooltip();
                    }

                    const max = this.attendeesCount > 0 ? this.attendeesCount : 1;
                    const percentage = Math.min(
                        Math.round((questionResults.answer_count / max) * 100),
                        100
                    );
                    this.el.querySelector(".progress-bar").style.width = `${percentage}%`;

                    if (this.attendeesCount && this.attendeesCount > 0) {
                        const answerCount = Math.min(
                            questionResults.answer_count,
                            this.attendeesCount
                        );
                        const answerCountElement = this.el.querySelector(
                            ".o_survey_session_answer_count"
                        );
                        const progressBarTextElement = this.el.querySelector(
                            ".progress-bar.o_survey_session_progress_small span"
                        );
                        if (answerCountElement) {
                            answerCountElement.textContent = answerCount;
                        }
                        if (progressBarTextElement) {
                            progressBarTextElement.textContent = `${answerCount} / ${this.attendeesCount}`;
                        }
                    }
                }
            }),
            this.protectSyncAfterAsync(() => {
                // on failure, stop refreshing
                clearInterval(this.resultsRefreshInterval);
                delete this.resultsRefreshInterval;
            })
        );
    }

    /**
     * We refresh the attendees count every 2 seconds while the user is on the start screen.
     */
    refreshAttendeesCount() {
        this.waitFor(
            this.services.orm.read("survey.survey", [this.surveyId], ["session_answer_count"])
        ).then(
            this.protectSyncAfterAsync((result) => {
                if (result && result.length === 1) {
                    this.sessionAttendeesCountText = String(result[0].session_answer_count);
                }
            }),
            this.protectSyncAfterAsync((err) => {
                // on failure, stop refreshing
                clearInterval(this.attendeesRefreshInterval);
                console.error(err);
            })
        );
    }
}

registry.category("public.interactions").add("survey.survey_session_manage", SurveySessionManage);
