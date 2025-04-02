import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { SlideQuizFinishDialog } from "@website_slides/js/public/components/slide_quiz_finish_dialog/slide_quiz_finish_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { insertHtmlContent } from "@website_slides/js/utils";
import { escape } from "@web/core/utils/strings";
import { WebsiteSlidesCourseQuizQuestionForm } from "@website_slides/js/components/slides_course_quiz_question_form";

class WebsiteSlidesQuiz extends Interaction {
    dynamicContent = {
        ".o_wslides_quiz_answer": { "t-on-click.prevent": this.onAnswerClick },
        ".o_wslides_js_lesson_quiz_submit": { "t-on-click": this.onQuizSubmit },
        ".o_wslides_quiz_continue": { "t-on-click": this.onNextClick },
        ".o_wslides_js_lesson_quiz_reset": { "t-on-click": this.onResetClick },
        ".o_wslides_js_quiz_add": { "t-on-click": this.onCreateQuestionClick },
        ".o_wslides_js_quiz_edit_question": { "t-on-click": this.onEditQuestionClick },
        ".o_wslides_js_quiz_delete_question": { "t-on-click": this.onDeleteQuestionClick },
        ".o_wslides_js_quiz_add_quiz": {
            "t-att-class": () => ({
                "d-none": !this.showAddButton || this.quiz.questionCount > 0,
            }),
        },
        ".o_wslides_js_quiz_add_question": {
            "t-att-class": () => ({
                "d-none": !this.showAddButton || this.quiz.questionCount === 0,
            }),
        },
        ".o_wslides_js_lesson_quiz_question .o_wslides_js_quiz_edit_del,\
        .o_wslides_js_lesson_quiz_question .o_wslides_js_quiz_sequence_handler": {
            "t-att-class": () => ({ "d-none": !this.showEditOptions }),
        },
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
        this.sortable = this.services.sortable;
        this.dialog = this.services.dialog;

        this.slidesService = this.services.website_slides;
        this.bus = this.slidesService.bus;
        this.slide = this.slidesService.data.slide;
        this.channel = this.slidesService.data.channel;
        this.quiz = this.slidesService.data.quiz;
        this.user = this.slidesService.data.user;
        this.slidesService.registerBeforeJoin(this.saveQuizAnswersToSession.bind(this));
        this.slidesService.registerAfterJoin(this.afterJoin.bind(this));

        this.bindedSortable = null;
        this.showAddButton = true;
        this.showEditOptions = true;
        this.showValidationInfo = false;
        this.showResourceInfo = false;
        this.error = null;
    }

    start() {
        this.renderValidationInfo();
        this.bindSortable();
        this.checkLocationHref();
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

    destroy() {
        this.unbindSortable();
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
     * Allows to reorder the questions
     */
    bindSortable() {
        this.bindedSortable = this.sortable
            .create({
                ref: { el: this.el },
                handle: ".o_wslides_js_quiz_sequence_handler",
                elements: ".o_wslides_js_lesson_quiz_question",
                onDrop: this.reorderQuestions.bind(this),
                clone: false,
                placeholderClasses: [
                    "o_wslides_js_quiz_sequence_highlight",
                    "position-relative",
                    "my-3",
                ],
                applyChangeOnDrop: true,
            })
            .enable();
    }

    unbindSortable() {
        this.bindedSortable?.cleanup();
    }

    /**
     * Get all the questions ID from the displayed Quiz
     * @returns {Array}
     */
    getQuestionsIds() {
        const questionIds = [];
        for (const el of this.el.querySelectorAll(".o_wslides_js_lesson_quiz_question")) {
            questionIds.push(Number(el.dataset.questionId));
        }
        return questionIds;
    }

    /**
     * Modify visually the sequence of all the questions after
     * calling the _reorderQuestions RPC call.
     */
    modifyQuestionsSequence() {
        let index = 1;
        for (const sequenceEl of this.el.querySelectorAll(
            "span.o_wslides_quiz_question_sequence"
        )) {
            if (
                sequenceEl.closest(".o_wslides_js_lesson_quiz_question") ||
                sequenceEl.closest(".o_wslides_js_lesson_quiz_new_question")
            ) {
                // is inside an existing question or new one
                sequenceEl.textContent = index;
                index++;
            } else {
                // is inside form to edit a question => same index as previous element
                sequenceEl.textContent = index - 1;
            }
        }
        this.bus.trigger("questions_reordered");
    }

    /**
     * RPC call to resequence all the questions. It is called
     * after modifying the sequence of a question and also after
     * deleting a question.
     */
    async reorderQuestions() {
        await this.waitFor(this.orm.webResequence("slide.question", this.getQuestionsIds()));
        this.modifyQuestionsSequence();
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
            },
            containerEl
        );
        if (
            !this.user.public &&
            this.channel.enroll === "public" &&
            this.quiz.sessionAnswers.length > 0
        ) {
            // auto join course if already answered questions
            this.applySessionAnswers();
            this.slidesService.joinChannel(this.channel.id);
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
                userId: this.user.id,
            });
            this.el.dispatchEvent(
                new CustomEvent("slide_completed", {
                    bubbles: true,
                    detail: {
                        channelCompletion: this.channel.completion,
                    },
                })
            );
        }
        this.showEditOptions = false;
        this.renderAnswersHighlightingAndComments();
        this.renderValidationInfo();
        this.showResourceInfo = !this.slide.completed;
    }

    /**
     * Get all the question information after clicking on
     * the edit button
     * @returns {{id: *, sequence: number, text: *, answers: Array}}
     */
    getQuestionDetails(el) {
        const answers = [];
        for (const answerEl of el.querySelectorAll(".o_wslides_quiz_answer")) {
            const data = answerEl.dataset;
            answers.push({
                id: Number(data.answerId),
                text_value: data.text || "",
                is_correct: !!data.isCorrect,
                comment: data.comment || "",
            });
        }
        const data = el.dataset;
        return {
            id: Number(data.questionId),
            sequence: parseInt(el.querySelector(".o_wslides_quiz_question_sequence").textContent),
            text: data.title,
            answers,
        };
    }

    /**
     * If the slides has been called with the Add Quiz button on the slide list
     * it goes straight to the 'Add Quiz' button and clicks on it.
     */
    checkLocationHref() {
        if (window.location.href.includes("quiz_quick_create") && this.quiz.questionCount === 0) {
            this.onCreateQuestionClick();
        }
    }

    /**
     * When clicking on an answer, this one should be marked as "checked".
     */
    onAnswerClick(event) {
        if (!this.slide.completed) {
            for (const inputEl of event.currentTarget.querySelectorAll("input[type=radio]")) {
                inputEl.checked = true;
            }
        }

        // uncomment this to make answers persistent between reloads
        // this.saveQuizAnswersToSession();
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
     * Resets the completion of the slide so the user can take
     * the quiz again
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
     * After joining the course, we save the questions in the session
     * and reload the page to update the view.
     */
    async afterJoin() {
        await this.waitFor(this.saveQuizAnswersToSession());
        window.location.reload();
    }

    /**
     * When clicking on 'Add a Question' or 'Add Quiz' it
     * initialize a new QuestionForm to input the new
     * question.
     */
    onCreateQuestionClick() {
        const containerEl = this.el.querySelector(".o_wslides_js_lesson_quiz_new_question");
        this.showAddButton = false;
        const root = this.mountComponent(containerEl, WebsiteSlidesCourseQuizQuestionForm, {
            question: {
                sequence: this.quiz.questionCount + 1,
            },
            update: false,
            onSave: (renderedQuestion) => {
                const questionEls = this.el.querySelectorAll(".o_wslides_js_lesson_quiz_question");
                const lastQuestionEl = questionEls[questionEls.length - 1];
                if (lastQuestionEl) {
                    insertHtmlContent(this, renderedQuestion, lastQuestionEl, "afterend");
                } else {
                    window.location.reload();
                    // TODO
                    // this could be more efficient if there was a way to get the channel information from the server without reloading the page
                    // in such a case we could fetch the channel data, call slidesService.fetchQuiz + renderValidationInfo and not need to reload the page
                    // for this to work we would need to create the validationEl (see renderValidationInfo) which would not be part of the dom
                    // and insert it in this.el
                }
                this.quiz.questionCount++;
                this.showAddButton = true;
                root.destroy();
                this.updateContent();
            },
            onCancel: () => {
                this.showAddButton = true;
                root.destroy();
                this.updateContent();
            },
        });
    }

    /**
     * When clicking on the edit button of a question it
     * initializes a new QuestionForm component with the existing
     * question as input.
     */
    onEditQuestionClick(event) {
        const editedQuestionEl = event.currentTarget.closest(".o_wslides_js_lesson_quiz_question");
        const question = this.getQuestionDetails(editedQuestionEl);
        const root = this.mountComponent(
            editedQuestionEl,
            WebsiteSlidesCourseQuizQuestionForm,
            {
                question,
                update: true,
                onSave: (renderedQuestion) => {
                    insertHtmlContent(this, renderedQuestion, editedQuestionEl, "afterend");
                    editedQuestionEl.remove();
                    root.destroy();
                },
                onCancel: () => {
                    editedQuestionEl.classList.remove("d-none");
                    root.destroy();
                },
            },
            "afterend"
        );
        editedQuestionEl.classList.add("d-none");
    }

    /**
     * When clicking on the delete button of a question it toggles a modal
     * to confirm the deletion. When confirming it sends an RPC request to
     * delete the Question and triggers an event to delete it from the UI.
     */
    onDeleteQuestionClick(event) {
        const question = event.currentTarget.closest(".o_wslides_js_lesson_quiz_question");
        const questionId = parseInt(question.dataset.questionId);
        this.dialog.add(ConfirmationDialog, {
            title: _t("Delete Question"),
            body: markup(
                _t(
                    'Are you sure you want to delete this question "<strong>%s</strong>"?',
                    escape(question.dataset.title)
                )
            ),
            cancel: () => {},
            cancelLabel: _t("No"),
            confirm: async () => {
                if (this.isDestroyed) {
                    return;
                }
                await this.waitFor(this.orm.unlink("slide.question", [questionId]));
                this.el
                    .querySelector(
                        `.o_wslides_js_lesson_quiz_question[data-question-id="${questionId}"]`
                    )
                    .remove();
                this.quiz.questionCount--;
                this.reorderQuestions();
                if (
                    this.quiz.questionCount === 0 &&
                    !this.el.querySelector(".o_wsildes_quiz_question_input")
                ) {
                    this.showValidationInfo = false;
                }
            },
            confirmLabel: _t("Yes"),
        });
    }
}

export class WebsiteSlidesQuizNoFullscreen extends WebsiteSlidesQuiz {
    static selector = ".o_wslides_js_lesson_quiz";

    setup() {
        super.setup();
        const questions = this.extractQuestionsAndAnswers();
        const data = this.el.dataset;
        this.slidesService.setSlide({
            id: Number(data.id),
            name: data.name,
            category: data.slideCategory,
            canSelfMarkCompleted: !!data.canSelfMarkCompleted,
            canSelfMarkUncompleted: !!data.canSelfMarkUncompleted,
            completed: !!data.completed,
            hasNext: !!data.hasNext,
            nextSlideUrl: data.nextSlideUrl,
            hasQuestion: questions.length > 0,
        });
        this.slidesService.setQuiz({
            attemptsCount: Number(data.quizAttemptsCount),
            karmaMax: Number(data.quizKarmaMax),
            karmaGain: Number(data.quizKarmaGain),
            karmaWon: Number(data.quizKarmaWon || 0),
            answers: [],
            sessionAnswers: data.sessionAnswers || [],
            questions,
            questionCount: questions.length,
        });
        if (data.channelId) {
            this.slidesService.setChannel({
                id: Number(data.channelId),
                enroll: data.channelEnroll,
                requestedAccess: !!data.channelRequestedAccess,
                canUpload: !!data.channelCanUpload,
                isMember: !!data.isMember,
                isMemberOrInvited: !!data.isMemberOrInvited,
            });
        }
        this.slidesService.setUser({
            signupAllowed: !!data.signupAllowed,
        });
    }

    /**
     * Extract data from exiting DOM rendered server-side, to have the list of questions with their
     * relative answers.
     * This method should return the same format as /slide/quiz/get controller.
     *
     * @return {Array<Object>} list of questions with answers
     */
    extractQuestionsAndAnswers() {
        const questions = [];
        for (const questionEl of this.el.querySelectorAll(".o_wslides_js_lesson_quiz_question")) {
            const answers = [];
            for (const answerEl of questionEl.querySelectorAll(".o_wslides_quiz_answer")) {
                const answerData = answerEl.dataset;
                answers.push({
                    id: Number(answerData.answerId),
                    text: answerData.text,
                });
            }
            const questionData = questionEl.dataset;
            questions.push({
                id: Number(questionData.questionId),
                title: questionData.title,
                answer_ids: answers,
            });
        }
        return questions;
    }
}

class WebsiteSlidesQuizFullscreen extends WebsiteSlidesQuiz {
    static selector = ".o_wslides_fs_quiz_container";
}

registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesQuizNoFullscreen", WebsiteSlidesQuizNoFullscreen);
registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesQuizFullscreen", WebsiteSlidesQuizFullscreen);
