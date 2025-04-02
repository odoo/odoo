import { rpc } from "@web/core/network/rpc";
import { SlideQuizFinishDialog } from "@website_slides/js/public/components/slide_quiz_finish_dialog/slide_quiz_finish_dialog";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
import { session } from "@web/session";
import { user } from "@web/core/user";

export class WebsiteSlidesQuiz extends Interaction {
    static selector = ".o_wslides_js_quiz_container";
    dynamicContent = {
        ".o_wslides_js_lesson_quiz_reset": { "t-on-click": this.onResetClick },
        ".o_wslides_quiz_answer": { "t-on-click.prevent": this.onAnswerClick },
        ".o_wslides_js_lesson_quiz_submit": { "t-on-click": this.onQuizSubmit },
        ".o_wslides_quiz_continue": { "t-on-click": this.onNextClick },
        ".o_wslides_js_lesson_quiz_validation": {
            "t-att-class": () => ({ "d-none": !this.showValidationInfo }),
        },
        ".o_wslides_js_quiz_submit_error": {
            "t-att-class": () => ({ "d-none": !this.error }),
        },
        ".o_wslides_js_quiz_submit_error_text": {
            "t-out": () => this.error || "",
        },
        ".o_wslides_js_lesson_quiz_resource_info": {
            "t-att-class": () => ({ "d-none": !this.showResourceInfo }),
        },
    };

    setup() {
        this.orm = this.services.orm;
        this.dialog = this.services.dialog;

        this.slidesService = this.services.website_slides;
        this.slide = this.slidesService.data.slide;
        this.channel = this.slidesService.data.channel;
        this.quiz = this.slidesService.data.quiz;
        this.slidesService.registerBeforeJoin(this.saveQuizAnswersToSession.bind(this));
        this.slidesService.registerAfterJoin(this.afterJoin.bind(this));

        this.showValidationInfo = false;
        this.showResourceInfo = false;
        this.error = null;
    }

    start() {
        this.renderValidationInfo();
        const numAnswers = this.quiz.sessionAnswers.length;
        if (!this.channel.isMember) {
            this.renderJoinButton();
        } else if (numAnswers > 0) {
            this.applySessionAnswers();
            if (numAnswers >= this.quiz.questionCount) {
                this.onQuizSubmit();
            }
        }
        this.updateContent();
    }

    /**
     * Update validation box (karma, buttons)
     */
    async renderValidationInfo() {
        const validationEl = this.el.querySelector(".o_wslides_js_lesson_quiz_validation");
        if (!validationEl) {
            return;
        }
        validationEl.replaceChildren();
        this.renderAt(
            "slide.slide.quiz.validation",
            {
                ...this.slidesService.data,
                redirectURL: encodeURIComponent(document.URL),
                signupAllowed: !!document.querySelector('.o_wslides_fs_main, .o_wslides_js_lesson_quiz').dataset.signupAllowed,
                isPublicUser: session.is_public,
            },
            validationEl
        );
        this.showValidationInfo = true;
    }

    /**
     * Renders the button to join a course.
     * If the user is logged in, the course is public, and the user has previously tried to
     * submit answers, we automatically attempt to join the course.
     */
    async renderJoinButton() {
        const containerEl = this.el.querySelector(".o_wslides_join_course_widget");
        if (!containerEl) {
            return;
        }
        this.renderAt(
            "slide.course.join",
            {
                ...this.slidesService.data,
                joinMessage: _t("Join & Submit"),
                isPublicUser: session.is_public,
            },
            containerEl
        );
        if (
            !session.is_public &&
            this.channel.enroll === "public" &&
            this.quiz.sessionAnswers.length > 0
        ) {
            // auto join course if already answered questions
            this.applySessionAnswers();
            this.slidesService.joinChannel(this.channel.id);
        }
    }

    showErrorMessage(errorCode) {
        let message = _t("There was an error validating this quiz.");
        if (errorCode === "slide_quiz_incomplete") {
            message = _t("All questions must be answered!");
        } else if (errorCode === "slide_quiz_done") {
            message = _t("This quiz is already done. Retaking it is not possible.");
        } else if (errorCode === "public_user") {
            message = _t("You must be logged to submit the quiz.");
        }
        this.error = message;
    }

    hideErrorMessage() {
        this.error = null;
        this.updateContent();
    }

    /**
     * Decorate the answers according to state
     */
    disableAnswers() {
        for (const el of this.el.querySelectorAll(".o_wslides_js_lesson_quiz_question")) {
            el.classList.add("completed-disabled");
        }
        for (const el of this.el.querySelectorAll("input[type='radio'")) {
            el.disabled = this.slide.completed;
        }
    }

    /**
     * Decorate the answer inputs according to the correction and adds the answer comment if
     * any.
     */
    renderAnswersHighlightingAndComments() {
        for (const questionEl of this.el.querySelectorAll(".o_wslides_js_lesson_quiz_question")) {
            const questionId = Number(questionEl.dataset.questionId);
            const isCorrect = this.quiz.answers[questionId].is_correct;
            for (const answerEl of questionEl.querySelectorAll("a.o_wslides_quiz_answer")) {
                for (const iconEl of answerEl.querySelectorAll("i.fa")) {
                    iconEl.classList.add("d-none");
                }
                if (answerEl.querySelector("input[type=radio]").checked) {
                    if (isCorrect) {
                        answerEl.classList.remove("list-group-item-danger");
                        answerEl.classList.add("list-group-item-success");
                        answerEl.querySelector("i.fa-check-circle").classList.remove("d-none");
                    } else {
                        answerEl.classList.remove("list-group-item-success");
                        answerEl.classList.add("list-group-item-danger");
                        answerEl.querySelector("i.fa-times-circle").classList.remove("d-none");
                        answerEl.querySelector("label input").checked = false;
                    }
                } else {
                    answerEl.classList.remove("list-group-item-danger", "list-group-item-success");
                    answerEl.querySelector("i.fa-circle").classList.remove("d-none");
                }
            }
            const comment = this.quiz.answers[questionId].comment;
            if (comment) {
                questionEl.querySelector(".o_wslides_quiz_answer_info").classList.remove("d-none");
                questionEl.querySelector(".o_wslides_quiz_answer_comment").textContent = comment;
            }
        }
    }

    /**
     * Get the quiz answers filled in by the User
     */
    getQuizAnswers() {
        const answers = [];
        for (const inputEl of this.el.querySelectorAll("input[type=radio]:checked")) {
            answers.push(parseInt(inputEl.value));
        }
        return answers;
    }

    /**
     * Submit a quiz and get the correction. It will display messages
     * according to quiz result.
     */
    async onQuizSubmit() {
        const data = await this.waitFor(
            rpc("/slides/slide/quiz/submit", {
                slide_id: this.slide.id,
                answer_ids: this.getQuizAnswers(),
            })
        );
        if (data.error) {
            this.showErrorMessage(data.error);
            return;
        } else {
            this.hideErrorMessage();
        }

        this.slide.completed = data.completed;
        this.channel.completion = data.channel_completion;

        // three of the rankProgress properties are HTML messages, mark if set
        const rankProgress = data.rankProgress;
        if ("description" in rankProgress) {
            rankProgress.description = markup(rankProgress.description || "");
            rankProgress.previous_rank.motivational = markup(
                rankProgress.previous_rank.motivational || ""
            );
            rankProgress.new_rank.motivational = markup(rankProgress.new_rank.motivational || "");
        }

        this.slidesService.setQuiz({
            answers: data.answers,
            karmaWon: data.quizKarmaWon,
            karmaGain: data.quizKarmaGain,
            attemptsCount: data.quizAttemptsCount,
            rankProgress: rankProgress,
        });

        if (this.slide.completed) {
            this.disableAnswers();
            this.dialog.add(SlideQuizFinishDialog, {
                quiz: this.quiz,
                hasNext: this.slide.hasNext,
                onClickNext: (event) => {
                    if (!this.isDestroyed) {
                        this.onNextClick(event);
                    }
                },
                userId: user.userId,
            });
            this.el.dispatchEvent(new CustomEvent("slide_completed", { bubbles: true }));
        }
        this.renderAnswersHighlightingAndComments();
        this.renderValidationInfo();
        this.showResourceInfo = !this.slide.completed;
    }

    /**
     * When clicking on an answer, this one should be marked as "checked".
     */
    onAnswerClick(event) {
        if (!this.slide.completed) {
            event.currentTarget.querySelector("input[type=radio]").checked = true;
        }

        // uncomment this to make answers persistent between reloads
        // this.saveQuizAnswersToSession();
    }

    /**
     * Resets the completion of the slide so the user can take
     * the quiz again (Only visible in normal view)
     */
    async onResetClick() {
        await this.waitFor(
            rpc("/slides/slide/quiz/reset", {
                slide_id: this.slide.id,
            })
        );
        window.location.reload();
    }

    /**
     * Triggering an event to switch to next slide
     */
    onNextClick() {
        if (this.slide.hasNext) {
            this.slidesService.bus.trigger("slide_go_next");
        }
    }

    /**
     * Saves the answers from the user and redirect the user to the
     * specified url
     */
    saveQuizAnswersToSession() {
        this.hideErrorMessage();
        return rpc("/slides/slide/quiz/save_to_session", {
            quiz_answers: { slide_id: this.slide.id, slide_answers: this.getQuizAnswers() },
        });
    }

    /**
     * Will check if we have answers coming from the session and re-apply them.
     */
    applySessionAnswers() {
        if (this.quiz.sessionAnswers.length === 0) {
            return;
        }
        for (const questionEl of this.el.querySelectorAll(".o_wslides_js_lesson_quiz_question")) {
            for (const answerEl of questionEl.querySelectorAll("a.o_wslides_quiz_answer")) {
                if (
                    !answerEl.querySelector("input[type=radio]").checked &&
                    this.quiz.sessionAnswers.includes(Number(answerEl.dataset.answerId))
                ) {
                    for (const inputEl of answerEl.querySelectorAll("input[type=radio]")) {
                        inputEl.checked = true;
                    }
                }
            }
        }
        // reset answers coming from the session
        this.quiz.sessionAnswers = [];
    }

    /**
     * After joining the course, we save the questions in the session
     * and reload the page to update the view.
     */
    async afterJoin() {
        await this.waitFor(this.saveQuizAnswersToSession());
        window.location.reload();
    }
}

registry.category("public.interactions").add("website_slides.WebsiteSlidesQuiz", WebsiteSlidesQuiz);
