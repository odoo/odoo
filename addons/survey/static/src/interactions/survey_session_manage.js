import { preloadBackground } from "@survey/js/survey_preload_image_mixin";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { browser } from "@web/core/browser/browser";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { fadeIn, fadeOut } from "@survey/utils";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

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
        _document: {
            "t-on-keydown": this.onKeyDown,
        },
        ".o_survey_session_copy": {
            "t-on-click.prevent": this.onCopySessionLink,
        },
        ".o_survey_session_navigation_next": {
            "t-on-click.prevent": this.onNext,
            "t-att-class": () => ({
                "d-none":
                    this.isSessionClosed ||
                    (this.isLastQuestion && this.currentScreen === "leaderboardFinal"),
            }),
        },
        ".o_survey_session_navigation_previous": {
            "t-on-click.prevent": this.onBack,
            "t-att-class": () => ({ "d-none": this.isFirstQuestion || this.isSessionClosed }),
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
        ".o_survey_session_results": {
            "t-att-class": () => ({
                "d-none": this.isSessionClosed || this.leaderboardIsFadingOut || this.hideResults,
            }),
            "t-on-setDisplayNone": () => {
                // The leaderboard interaction will send a setDisplayNone event
                // after finishing its fade-in animation.
                this.hideResults = true;
            },
        },
        ".o_survey_session_description_done": {
            "t-att-class": () => ({ "d-none": !this.isSessionClosed }),
        },
    };

    setup() {
        if (this.el.dataset.isSessionClosed) {
            this.isSessionClosed = true;
            this.el.classList.remove("invisible");
            return;
        }
        this.fadeInOutTime = 500;
        this.answersRefreshDelay = 2000;
        // Flags used in dynamicContent
        this.isSessionClosed = false;
        this.leaderboardIsFadingOut = false;
        this.hideResults = false;
        // Elements related to other interactions
        this.chartEl = this.el.querySelector(".o_survey_session_chart");
        this.leaderboardEl = this.el.querySelector(".o_survey_session_leaderboard");
        this.timerEl = this.el.querySelector(".o_survey_timer_container .o_survey_timer");
        this.textAnswersEl = this.el.querySelector(".o_survey_session_text_answers_container");
        // General survey props
        this.surveyId = parseInt(this.el.dataset.surveyId);
        this.attendeesCount = this.el.dataset.attendeesCount
            ? parseInt(this.el.dataset.attendeesCount, 10)
            : 0;
        this.surveyHasConditionalQuestions = this.el.dataset.surveyHasConditionalQuestions;
        this.surveyAccessToken = this.el.dataset.surveyAccessToken;
        this.isStartScreen = this.el.dataset.isStartScreen;
        this.isFirstQuestion = this.el.dataset.isFirstQuestion;
        this.isLastQuestion = this.el.dataset.isLastQuestion;
        this.surveyLastTriggeringAnswers = JSON.parse(
            this.el.dataset.surveyLastTriggeringAnswers || "[]"
        );
        // Scoring props
        this.isScoredQuestion = this.el.dataset.isScoredQuestion;
        this.sessionShowLeaderboard = this.el.dataset.sessionShowLeaderboard;
        this.hasCorrectAnswers = this.el.dataset.hasCorrectAnswers;
        // Display props
        this.showBarChart = this.el.dataset.showBarChart;
        this.showTextAnswers = this.el.dataset.showTextAnswers;
        // Question transition
        this.stopNextQuestion = false;
        // Background Management
        this.refreshBackground = this.el.dataset.refreshBackground;
        // Prepare the copy link tooltip
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
        this.registerCleanup(() => {
            this.copyBtnPopover?.dispose();
            this.copyBtnTooltip?.dispose();
        });
        // Attendees count & navigation label
        this.sessionAttendeesCountText = "";
        this.sessionNavigationNextLabel = "";
        // Show the page and start the timer
        this.el.classList.remove("invisible");
        this.setupIntervals();
    }

    async willStart() {
        // If a chart is present, we wait for the chart interaction to be ready.
        // The presence of the class `chart_is_ready` means that the chart was
        // ready before us, so we don't need to wait (see survey_session_chart)
        if (this.chartEl && !this.chartEl.classList.contains("chart_is_ready")) {
            let resolveChartPromise;
            const chartPromise = new Promise(function (resolve) {
                resolveChartPromise = resolve;
            });
            this.env.bus.addEventListener("SURVEY:CHART_INTERACTION_STARTED", resolveChartPromise);
            await chartPromise;
        }
    }

    start() {
        this.setupCurrentScreen();
        this.startTimer();
        // Check if we are loading this page because the user clicked on 'previous'
        if (this.el.dataset.goingBack) {
            this.chartUpdateState({ showInputs: true, showAnswers: true });
            if (this.sessionShowLeaderboard && this.isScoredQuestion) {
                this.currentScreen = "leaderboard";
                this.leaderboardEl.dispatchEvent(
                    new CustomEvent("showLeaderboard", {
                        detail: {
                            fadeOut: false,
                            isScoredQuestion: this.isScoredQuestion,
                        },
                    })
                );
            } else {
                this.currentScreen = "results";
            }
            this.refreshResults();
        }
    }

    /**
     * Copies the survey URL link to the clipboard.
     * We avoid having to print the URL in a standard text input.
     *
     * @param {MouseEvent} ev
     */
    async onCopySessionLink(ev) {
        const copyBtnTooltipHideDelay = 800;
        this.copyBtnTooltip?.dispose();
        delete this.copyBtnTooltip;
        this.copyBtnPopover = window.Popover.getOrCreateInstance(ev.currentTarget, {
            content: _t("Copied!"),
            trigger: "manual",
            placement: "right",
            container: "body",
            offset: "0, 3",
        });
        await this.waitFor(
            browser.navigator.clipboard.writeText(ev.currentTarget.innerText.trim())
        );
        this.protectSyncAfterAsync(() => {
            this.copyBtnPopover.show();
            this.waitForTimeout(() => this.copyBtnPopover.hide(), copyBtnTooltipHideDelay);
        })();
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
                this.chartUpdateState({ showInputs: true });
                break;
            case "results":
                this.chartUpdateState({ showAnswers: true });
                // when showing results, stop refreshing answers
                clearInterval(this.resultsRefreshInterval);
                delete this.resultsRefreshInterval;
                break;
            case "leaderboard":
            case "leaderboardFinal":
                if (!this.currentScreen.startsWith("leaderboard")) {
                    this.leaderboardEl.dispatchEvent(
                        new CustomEvent("showLeaderboard", {
                            detail: {
                                fadeOut: true,
                                isScoredQuestion: this.isScoredQuestion,
                            },
                        })
                    );
                }
                break;
            default:
                if (!this.isLastQuestion || !this.sessionShowLeaderboard) {
                    this.goToNextQuestion();
                }
                break;
        }
        this.currentScreen = screenToDisplay;
        // To avoid a flicker, we do not update the tooltip when going to the
        // next question, as it will be done anyway in "setupCurrentScreen"
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
                this.chartUpdateState({ showInputs: false });
                break;
            case "userInputs":
                this.chartUpdateState({ showAnswers: false });
                // resume refreshing answers if necessary
                if (!this.resultsRefreshInterval) {
                    this.resultsRefreshInterval = setInterval(
                        this.refreshResults.bind(this),
                        this.answersRefreshDelay
                    );
                }
                break;
            case "results":
                if (this.isScoredQuestion || this.isLastQuestion) {
                    this.leaderboardEl.dispatchEvent(new Event("hideLeaderboard"));
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
        // To avoid a flicker, we do not update the tooltip when going to the
        // next question, as it will be done anyway in "setupCurrentScreen"
        if (!["question", "nextQuestion"].includes(screenToDisplay)) {
            this.updateNextScreenTooltip();
        }
    }

    /**
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
     * (For details about which screen shows what, see 'onNext')
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
            if (this.isLastQuestion) {
                return "leaderboardFinal";
            } else if (
                ["question", "userInputs", "results"].includes(this.currentScreen) &&
                this.isScoredQuestion
            ) {
                return "leaderboard";
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
        // Prevent the results to appear before the leaderboard is out
        this.leaderboardIsFadingOut = true;
        this.isStartScreen = false;
        // start the fadeout animation
        let resolveFadeOut;
        const fadeOutPromise = new Promise(function (resolve) {
            resolveFadeOut = resolve;
        });
        fadeOut(this.el, this.fadeInOutTime, () => {
            this.leaderboardIsFadingOut = false;
            resolveFadeOut();
        });
        // background management
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
        // rpc call to get the next question
        this.nextQuestion = await this.waitFor(
            rpc(`/survey/session/next_question/${this.surveyAccessToken}`, {
                go_back: goBack,
            })
        );
        let preloadBgPromise;
        if (this.refreshBackground && this.nextQuestion.background_image_url) {
            preloadBgPromise = preloadBackground(this.nextQuestion.background_image_url);
        } else {
            preloadBgPromise = Promise.resolve();
        }
        // await both the fadeout and the rpc
        await this.waitFor(Promise.all([fadeOutPromise, preloadBgPromise]));
        this.protectSyncAfterAsync(() => this.onNextQuestionDone(goBack))();
    }

    /**
     * Refresh the screen with the next question's rendered template.
     *
     * @param {boolean} goBack Whether we are going back to the previous question or not
     */
    async onNextQuestionDone(goBack) {
        if (!this.nextQuestion.question_html) {
            this.isSessionClosed = true;
            this.onEndSessionClick();
            return;
        }

        const parser = new DOMParser();
        const newContent = parser.parseFromString(this.nextQuestion.question_html, "text/html").body
            .firstChild;
        newContent.style.opacity = 0;

        if (goBack) {
            // If the question is loaded with goBack flag, we need to start
            // from the leaderboard screen. This is achieved by adding a
            // data-going-back attribute to the newContentChild
            newContent.dataset.goingBack = true;
        }

        // Background Management
        if (this.refreshBackground) {
            const surveyBackground = newContent.querySelector("div.o_survey_background");
            if (surveyBackground) {
                surveyBackground.style.backgroundImage = `url(${this.nextQuestion.background_image_url})`;
                surveyBackground.classList.remove("o_survey_background_transition");
            }
        }

        this.el.parentNode.replaceChild(newContent, this.el);

        // Fade in the new content, wait for the interactions to be ready and then
        // stop the interaction on the old content (the one execuing this code)
        fadeIn(newContent, this.fadeInOutTime);
        await this.services["public.interactions"].startInteractions(newContent);
        this.services["public.interactions"].stopInteractions(this.el);
    }

    /**
     * Marks this session as 'done' and redirects the user to the results based on the clicked link.
     *
     * @private
     */
    async onEndSessionClick(ev) {
        // ev could not exist (onNextQuestionDone )
        const showResults = ev?.currentTarget?.dataset?.showResults;
        await this.waitFor(
            this.services.orm.call("survey.survey", "action_end_session", [[this.surveyId]])
        );
        this.protectSyncAfterAsync(() => {
            if (showResults) {
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
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "arrowright" || hotkey === "space") {
            this.onNext(ev);
        } else if (hotkey === "arrowleft") {
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
        this.chartUpdateState({ showInputs: this.currentScreen === "userInputs" });
        this.updateNextScreenTooltip();
    }

    /**
     * Send a CustomEvent to the chart interaction to update its state.
     * Possible options are:
     *  - showInputs: boolean, show attendees survey.user_input.lines
     *  - showAnswers: boolean, show the question survey.question.answers
     *  - questionStatistics: object, chart data (counts / labels / ...)
     */
    chartUpdateState(options) {
        this.chartEl?.dispatchEvent(
            new CustomEvent("updateState", {
                detail: options,
            })
        );
    }

    /**
     * Updates the tooltip for current page (on right arrow icon for 'Next' content).
     * this method will be called on Clicking of Next and Previous Arrow to show the
     * tooltip for the Next Content.
     */
    updateNextScreenTooltip() {
        let tooltip;
        if (this.currentScreen === "startScreen") {
            tooltip = nextPageTooltips.startScreen;
        } else if (
            this.isLastQuestion &&
            !this.surveyHasConditionalQuestions &&
            !this.isScoredQuestion &&
            !this.sessionShowLeaderboard
        ) {
            tooltip = nextPageTooltips.closingWords;
        } else {
            const nextScreen = this.getNextScreen();
            if (nextScreen === "nextQuestion" || this.surveyHasConditionalQuestions) {
                tooltip = nextPageTooltips.nextQuestion;
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
     * Setup the two refresh intervals of 2 seconds for our interaction:
     * - The refresh of attendees count (only on the start screen)
     * - The refresh of results (used for chart/text answers/progress bar)
     */
    setupIntervals() {
        if (this.isStartScreen) {
            this.attendeesRefreshInterval = setInterval(
                this.refreshAttendeesCount.bind(this),
                this.answersRefreshDelay
            );
        } else {
            if (this.attendeesRefreshInterval) {
                clearInterval(this.attendeesRefreshInterval);
            }
            if (!this.resultsRefreshInterval) {
                this.resultsRefreshInterval = setInterval(
                    this.refreshResults.bind(this),
                    this.answersRefreshDelay
                );
            }
        }
    }

    /**
     * Will start the question timer so that the host may know when the question is done to display
     * the results and the leaderboard.
     *
     * If the question is scored, the timer ending triggers the display of attendees inputs.
     */
    startTimer(el) {
        const surveyManagerEl = el || this.el;
        const timerData = surveyManagerEl.dataset;
        const questionTimeLimitReached = !!timerData.questionTimeLimitReached;
        const timeLimitMinutes = Number(timerData.timeLimitMinutes);
        const hasAnswered = !!timerData.hasAnswered;
        if (this.timerEl && !questionTimeLimitReached && !hasAnswered && timeLimitMinutes) {
            this.addListener(surveyManagerEl, "time_up", async () => {
                if (this.currentScreen === "question" && this.isScoredQuestion) {
                    this.onNext();
                }
            });
            this.timerEl.dispatchEvent(
                new CustomEvent("start_timer", {
                    detail: {
                        timeLimitMinutes: timeLimitMinutes,
                        timer: timerData.timer,
                    },
                })
            );
        }
    }

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

                    if (
                        !this.isStartScreen &&
                        this.showBarChart &&
                        questionResults.question_statistics_graph
                    ) {
                        const parsedStatistics = JSON.parse(
                            questionResults.question_statistics_graph
                        );
                        if (parsedStatistics.length > 0) {
                            this.chartUpdateState({ questionStatistics: parsedStatistics });
                        }
                    } else if (!this.isStartScreen && this.showTextAnswers) {
                        this.textAnswersEl.dispatchEvent(
                            new CustomEvent("updateTextAnswers", {
                                detail: {
                                    questionType: this.el.dataset.questionType,
                                    inputLineValues: questionResults.input_line_values,
                                },
                            })
                        );
                    }

                    // Update the last question next screen tooltip depending on
                    // the selected answers. If a selected answer triggers a
                    // conditional question, the last question may no longer be
                    // the last (see PR odoo/odoo#212890).
                    if (this.surveyLastTriggeringAnswers.length) {
                        this.isLastQuestion =
                            !questionResults.answer_count ||
                            !this.surveyLastTriggeringAnswers.some((answerId) =>
                                questionResults.selected_answers.includes(answerId)
                            );
                        this.updateNextScreenTooltip();
                    }

                    const progressBar = this.el.querySelector(".progress-bar");
                    if (progressBar) {
                        const max = this.attendeesCount > 0 ? this.attendeesCount : 1;
                        const percentage = Math.min(
                            Math.round((questionResults.answer_count / max) * 100),
                            100
                        );
                        progressBar.style.width = `${percentage}%`;
                    }

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
                // onRejected, stop refreshing
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
