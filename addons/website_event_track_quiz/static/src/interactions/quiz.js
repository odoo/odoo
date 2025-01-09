import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";

/**
 * This widget is responsible of displaying quiz questions and propositions. Submitting the quiz will fetch the
 * correction and decorate the answers according to the result. Error message can be displayed.
 *
 * This widget can be attached to DOM rendered server-side by `gamification_quiz.`
 */
export class Quiz extends Interaction {
    // To match template: 'quiz.main',
    //static selector = ".o_quiz_main div:has(> div > div.o_quiz_js_quiz_question)";
    //static selector = "div:has(> div > div.o_quiz_js_quiz_question)";
    static selector = ".o_quiz_main";
    dynamicContent = {
        ".o_quiz_quiz_answer": {
            "t-on-click.prevent.withTarget": this.onAnswerClick,
        },
        ".o_quiz_js_quiz_submit": {
            "t-on-click": this.onSubmitQuizClick,
        },
        ".o_quiz_js_quiz_reset": {
            "t-on-click": this.onResetQuizClick,
        },
        ".o_quiz_js_quiz_question": {
            "t-att-class": () => ({
                "completed-disabled": this.track.completed,
            }),
        },
        "input[type=radio]": {
            "t-att-disabled": () => this.track.completed || undefined,
        },
    };

    setup() {
        const questions = this.extractQuestionsAndAnswers();
        const data = this.el.querySelector(".o_quiz_js_quiz").dataset;
        this.track = {
            id: parseInt(data.id) || 0,
            name: data.name || "",
            eventId: parseInt(data.eventId) || "",
            completed: data.completed || false,
            isMember: data.isMember || false,
            progressBar: data.progressBar || false,
            isEventUser: data.isEventUser || false,
            repeatable: data.repeatable || false,
        };
        this.quiz = {
            questions: questions,
            questionsCount: questions.length,
            sessionAnswers: data.sessionAnswers || [],
            quizKarmaMax: data.quizKarmaMax,
            quizKarmaWon: data.quizKarmaWon,
            quizKarmaGain: data.quizKarmaGain,
            quizPointsGained: data.quizPointsGained,
            quizAttemptsCount: data.quizAttemptsCount,
        };
        this.isMember = this.track.isMember || false;
        this.userId = user.userId;
        this.redirectURL = encodeURIComponent(document.URL);
    }

    /**
     * Overridden to add custom rendering behavior upon start of the widget.
     *
     * If the user has answered the quiz before having joined the course, we check
     * their answers (saved into their session) here as well.
     */
    start() {
        this.renderValidationInfo();
    }

    alertShow(alertCode) {
        let message = _t("There was an error validating this quiz.");
        if (alertCode === "quiz_incomplete") {
            message = _t("All questions must be answered!");
        } else if (alertCode === "quiz_done") {
            message = _t("This quiz is already done. Retaking it is not possible.");
        }
        this.services.notification.add(message, {
            type: "warning",
            title: _t("Quiz validation error"),
            sticky: true,
        });
    }

    /**
     * Get the quiz answers filled in by the User
     */
    getQuizAnswers() {
        return [...this.el.querySelectorAll("input[type=radio]:checked")].map((el) => parseInt(el.value));
    }

    /**
     * Decorate the answer inputs according to the correction and adds the answer comment if
     * any.
     */
    renderAnswersHighlightingAndComments() {
        for (const questionEl of this.el.querySelectorAll(".o_quiz_js_quiz_question")) {
            const questionId = questionEl.dataset.questionId;
            const answer = this.quiz.answers[questionId];
            for (const answerEl of questionEl.querySelectorAll("a.o_quiz_quiz_answer")) {
                for (const iEl of answerEl.querySelectorAll("i.fa")) {
                    iEl.classList.add("d-none");
                }
                if (answerEl.querySelector("input[type=radio]").checked) {
                    if (answer.is_correct) {
                        answerEl.querySelector("i.fa-check-circle").classList.remove("d-none");
                    } else {
                        answerEl.querySelector("label input").checked = false;
                        answerEl.querySelector("i.fa-times-circle").classList.remove("d-none");
                    }
                    if (answer.awarded_points > 0) {
                        this.renderAt("quiz.badge", {
                            "answer": answer,
                        }, answerEl);
                    }
                } else {
                    answerEl.querySelector("i.fa-circle").classList.remove("d-none");
                }
            }
            const listEl = questionEl.querySelector(".list-group");
            if (listEl) {
                this.renderAt("quiz.comment", {
                    "answer": answer,
                }, listEl);
            }
        }
    }

    /*
     * Update validation box (karma, buttons) according to widget state
     */
    renderValidationInfo() {
        const validationEl = this.el.querySelector(".o_quiz_js_quiz_validation");
        validationEl.replaceChildren();
        this.renderAt("quiz.validation", {
            "widget": this,
        }, validationEl);
    }

    /**
     * Remove the answer decorators
     */
    resetQuiz() {
        for (const questionEl of this.el.querySelectorAll(".o_quiz_js_quiz_question")) {
            for (const answerEl of questionEl.querySelectorAll("a.o_quiz_quiz_answer")) {
                for (const iEl of answerEl.querySelectorAll("i.fa")) {
                    iEl.classList.add("d-none");
                }
                answerEl.querySelector("i.fa-circle").classList.remove("d-none");
                answerEl.querySelector("span.badge")?.remove();
                answerEl.querySelector("input[type=radio]").checked = false;
            }
            const infoEl = questionEl.querySelector(".o_quiz_quiz_answer_info");
            infoEl?.remove();
        }
        this.track.completed = false;
        this.renderValidationInfo();
    }

    /**
     * Submit a quiz and get the correction. It will display messages
     * according to quiz result.
     */
    async onSubmitQuizClick() {
        const data = await this.waitFor(rpc("/event_track/quiz/submit", {
            event_id: this.track.eventId,
            track_id: this.track.id,
            answer_ids: this.getQuizAnswers(),
        }));
        if (data.error) {
            this.alertShow(data.error);
        } else {
            this.quiz = Object.assign(this.quiz, data);
            this.quiz.quizPointsGained = data.quiz_points;
            if (data.quiz_completed) {
                this.track.completed = data.quiz_completed;
            }
            this.renderAnswersHighlightingAndComments();
            this.renderValidationInfo();
        }
        return data;
    }

    /**
     * Extract data from exiting DOM rendered server-side, to have the list of questions with their
     * relative answers.
     * This method should return the same format as /gamification_quiz/quiz/get controller.
     *
     * @return {Array<Object>} list of questions with answers
     */
    extractQuestionsAndAnswers() {
        const questions = [];
        for (const questionEl of this.el.querySelectorAll(".o_quiz_js_quiz_question")) {
            const answers = [];
            for (const answerEl of questionEl.querySelectorAll(".o_quiz_quiz_answer")) {
                answers.push({
                    id: answerEl.dataset.answerId,
                    text: answerEl.dataset.text,
                });
            }
            questions.push({
                id: questionEl.dataset.questionId,
                title: questionEl.dataset.title,
                answer_ids: answers,
            });
        }
        return questions;
    }

    /**
     * When clicking on an answer, this one should be marked as "checked".
     * @param OdooEvent ev
     * @param currentTargetEl
     */
    onAnswerClick(ev, currentTargetEl) {
        if (!this.track.completed) {
            currentTargetEl.querySelector("input[type=radio]").checked = true;
        }
    }

    /**
     * Resets the completion of the track so the user can take
     * the quiz again
     */
    async onResetQuizClick() {
        await this.waitFor(rpc("/event_track/quiz/reset", {
            event_id: this.track.eventId,
            track_id: this.track.id
        }));
        this.resetQuiz();
    }
}

registry
    .category("public.interactions")
    .add("website_event_track_quiz.quiz", Quiz);
