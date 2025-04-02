import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getDataFromEl } from "@web/public/utils";
import { redirect } from "@web/core/utils/urls";
import { WebsiteSlidesCoursePage } from "./slides_course_page";
import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { SlideQuizFinishDialog } from "@website_slides/js/public/components/slide_quiz_finish_dialog/slide_quiz_finish_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

// TODO: replace textContent with t-out
// TODO: replace classList with t-att-class
// TODO: check that should not replace some querySelectors with querySelectorAll
// TODO: solve bug showing errors when should not

class WebsiteSlidesQuiz extends Interaction {
    dynamicContent = {
        ".o_wslides_quiz_answer": { "t-on-click.prevent": this.onAnswerClick },
        ".o_wslides_js_lesson_quiz_submit": { "t-on-click": this.onQuizSubmit },
        ".o_wslides_quiz_continue": { "t-on-click": this.onNextClick },
        ".o_wslides_js_lesson_quiz_reset": { "t-on-click": this.onResetClick },
        ".o_wslides_js_quiz_add": { "t-on-click": this.onCreateQuestionClick },
        ".o_wslides_js_quiz_edit_question": { "t-on-click": this.onEditQuestionClick },
        ".o_wslides_js_quiz_delete_question": { "t-on-click": this.onDeleteQuestionClick },
        ".o_wsildes_quiz_question_input": {
            "t-on-display_created_question": this.onDisplayCreatedQuestion,
            "t-on-display_updated_question": this.onDisplayUpdatedQuestion,
            "t-on-reset_display": this.onResetDisplay,
        },
        ".o_wslides_js_quiz_add_quiz": {
            "t-att-class": () => ({ "d-none": !this.showAddButton || this.data.questionCount > 0 }),
        },
        ".o_wslides_js_quiz_add_question": {
            "t-att-class": () => ({
                "d-none": !this.showAddButton || this.data.questionCount == 0,
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
        ".o_wslides_js_course_join_link": {
            "t-on-before_course_join": this.saveQuizAnswersToSession,
            "t-on-after_course_join": this.afterJoin,
        },
    };

    setup() {
        // TODO: remove unused fields
        this.orm = this.services.orm;
        this.sortable = this.services.sortable;
        this.dialog = this.services.dialog;

        this.quizService = this.services.slides_course_quiz;
        const courseJoinService = this.services.slides_course_join;
        this.data = this.quizService.get();
        courseJoinService.registerBeforeJoin(this.saveQuizAnswersToSession.bind(this));
        courseJoinService.registerAfterJoin(this.afterJoin.bind(this));

        this.bindedSortable = null;
        this.editedQuestionEls = {};
        this.showAddButton = true;
        this.showEditOptions = true;
        this.showValidationInfo = false;
        this.error = null;
    }

    start() {
        this.renderValidationInfo();
        this.bindSortable();
        this.checkLocationHref();
        if (!this.data.isMember) {
            this.renderJoinButton();
        } else if (this.data.sessionAnswers) {
            this.applySessionAnswers();
            this.onQuizSubmit();
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
            questionIds.push(getDataFromEl(el).questionId);
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
            // TODO: use t-out
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
    }

    /**
     * RPC call to resequence all the questions. It is called
     * after modifying the sequence of a question and also after
     * deleting a question.
     */
    async reorderQuestions() {
        await this.orm.webResequence("slide.question", this.getQuestionsIds());
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
            el.disabled = this.data.completed;
        }
    }

    /**
     * Decorate the answer inputs according to the correction and adds the answer comment if
     * any.
     */
    renderAnswersHighlightingAndComments() {
        for (const questionEl of this.el.querySelectorAll(".o_wslides_js_lesson_quiz_question")) {
            const questionId = getDataFromEl(questionEl).questionId;
            console.log(this.data);
            const isCorrect = this.data.answers[questionId].is_correct;
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
            const comment = this.data.answers[questionId].comment;
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
        if (!this.data.sessionAnswers || this.data.sessionAnswers.length === 0) {
            return;
        }
        for (const questionEl of this.el.querySelectorAll(".o_wslides_js_lesson_quiz_question")) {
            for (const answerEl of questionEl.querySelectorAll("a.o_wslides_quiz_answer")) {
                if (
                    !answerEl.querySelector("input[type=radio]").checked &&
                    this.data.sessionAnswers.includes(getDataFromEl(answerEl).answerId)
                ) {
                    for (const inputEl of answerEl.querySelectorAll("input[type=radio]")) {
                        inputEl.checked = true;
                    }
                }
            }
        }

        // reset answers coming from the session
        this.data.sessionAnswers = null;
    }

    /**
     * Update validation box (karma, buttons) according to widget state
     */
    renderValidationInfo() {
        const validationEl = this.el.querySelector(".o_wslides_js_lesson_quiz_validation");
        if (!validationEl) {
            return;
        }
        validationEl.replaceChildren();
        console.log(this.data);
        this.renderAt("slide.slide.quiz.validation", this.data, validationEl);
        this.showValidationInfo = true;
    }

    /**
     * Toggle additional resource info box
     * @param {Boolean} show - Whether show or hide the information
     */
    toggleAdditionalResourceInfo(show) {
        // TODO: use att-class and check if not child of this.el instead of document
        const resourceInfoEl = document.querySelector(".o_wslides_js_lesson_quiz_resource_info");
        if (resourceInfoEl) {
            show
                ? resourceInfoEl.classList.remove("d-none")
                : resourceInfoEl.classList.add("d-none");
        }
    }

    /**
     * Renders the button to join a course.
     * If the user is logged in, the course is public, and the user has previously tried to
     * submit answers, we automatically attempt to join the course.
     */
    renderJoinButton() {
        const containerEl = this.el.querySelector(".o_wslides_join_course_widget");
        if (!containerEl) {
            return;
        }
        this.renderAt(
            "slide.course.join",
            {
                channelEnroll: this.data.channelEnroll,
                isMemberOrInvited: this.data.isMemberOrInvited,
                joinMessage: _t("Join & Submit"),
            },
            containerEl
        );
        if (
            !this.data.publicUser &&
            this.data.channelEnroll === "public" &&
            this.data.sessionAnswers
        ) {
            // TODO: trigger event to join channel
            // courseJoinWidget.joinChannel(this.data.channelId);
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
        const data = await rpc("/slides/slide/quiz/submit", {
            slide_id: this.data.id,
            answer_ids: this.getQuizAnswers(),
        });
        if (data.error) {
            this.showErrorMessage(data.error);
            return;
        } else {
            this.hideErrorMessage();
        }
        Object.assign(this.data, data);
        const { rankProgress, completed, channel_completion: completion } = this.data;
        // three of the rankProgress properties are HTML messages, mark if set
        if ("description" in rankProgress) {
            rankProgress["description"] = markup(rankProgress["description"] || "");
            rankProgress["previous_rank"]["motivational"] = markup(
                rankProgress["previous_rank"]["motivational"] || ""
            );
            rankProgress["new_rank"]["motivational"] = markup(
                rankProgress["new_rank"]["motivational"] || ""
            );
        }
        if (completed) {
            this.disableAnswers();
            this.dialog.add(SlideQuizFinishDialog, {
                quiz: this.data,
                hasNext: this.data.hasNext,
                onClickNext: (event) => {
                    if (!this.isDestroyed) {
                        this.onNextClick(event);
                    }
                },
                userId: this.data.userId,
            });
            this.data.completed = true;
            this.el.dispatchEvent(
                new CustomEvent("slide_completed", {
                    bubbles: true,
                    detail: {
                        slideId: this.data.id,
                        channelCompletion: completion,
                        completed: true,
                    },
                })
            );
        }
        this.showEditOptions = false;
        this.renderAnswersHighlightingAndComments();
        this.renderValidationInfo();
        this.toggleAdditionalResourceInfo(!completed);
    }

    /**
     * Get all the question information after clicking on
     * the edit button
     * @returns {{id: *, sequence: number, text: *, answers: Array}}
     */
    getQuestionDetails(el) {
        const answers = [];
        for (const answerEl of el.querySelectorAll(".o_wslides_quiz_answer")) {
            const data = getDataFromEl(answerEl);
            answers.push({
                id: data.answerId,
                text_value: data.text,
                is_correct: data.isCorrect,
                comment: data.comment,
            });
        }
        const data = getDataFromEl(el);
        return {
            id: data.questionId,
            sequence: parseInt(el.querySelector(".o_wslides_quiz_question_sequence").textContent),
            text: data.title,
            answers: answers,
        };
    }

    /**
     * If the slides has been called with the Add Quiz button on the slide list
     * it goes straight to the 'Add Quiz' button and clicks on it.
     */
    checkLocationHref() {
        if (window.location.href.includes("quiz_quick_create") && this.data.questionCount === 0) {
            this.onCreateQuestionClick();
        }
    }

    /**
     * When clicking on an answer, this one should be marked as "checked".
     */
    onAnswerClick(event) {
        if (!this.data.completed) {
            for (const inputEl of event.currentTarget.querySelectorAll("input[type=radio]")) {
                inputEl.checked = true;
            }
        }
    }

    /**
     * Triggering an event to switch to next slide
     */
    onNextClick() {
        if (this.data.hasNext) {
            this.el.dispatchEvent(new Event("slide_go_next"));
        }
    }

    /**
     * Resets the completion of the slide so the user can take
     * the quiz again
     */
    async onResetClick() {
        await rpc("/slides/slide/quiz/reset", {
            slide_id: this.data.id,
        });
        window.location.reload();
    }

    /**
     * Saves the answers from the user and redirect the user to the
     * specified url
     */
    saveQuizAnswersToSession() {
        this.hideErrorMessage();

        return rpc("/slides/slide/quiz/save_to_session", {
            quiz_answers: { slide_id: this.data.id, slide_answers: this.getQuizAnswers() },
        });
    }

    /**
     * After joining the course, we save the questions in the session
     * and reload the page to update the view.
     */
    async afterJoin() {
        await this.saveQuizAnswersToSession();
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
        this.renderAt(
            "slide.quiz.question.input",
            {
                question: {},
                sequence: this.data.questionCount + 1,
                update: false,
            },
            containerEl
        );
    }

    /**
     * When clicking on the edit button of a question it
     * initialize a new QuestionFormWidget with the existing
     * question as inputs.
     */
    onEditQuestionClick(event) {
        const editedQuestionEl = event.currentTarget.closest(".o_wslides_js_lesson_quiz_question");
        const question = this.getQuestionDetails(editedQuestionEl);
        this.editedQuestionEls[question.id] = editedQuestionEl;
        this.quizService.updateQuestion(question);
        this.renderAt(
            "slide.quiz.question.input",
            {
                question,
                sequence: question.sequence,
                update: true,
            },
            editedQuestionEl,
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
                    `Are you sure you want to delete this question "<strong>${question.dataset.title}</strong>"?`
                )
            ),
            cancel: () => {},
            cancelLabel: _t("No"),
            confirm: async () => {
                await this.orm.unlink("slide.question", [questionId]);
                this.onDeleteQuestion(questionId);
            },
            confirmLabel: _t("Yes"),
        });
    }

    /**
     * Displays the created Question at the correct place (after the last question or
     * at the first place if there is no questions yet) It also displays the 'Add Question'
     * button or open a new QuestionFormWidget if the user wants to immediately add another one.
     */
    onDisplayCreatedQuestion(event) {
        const questionEls = this.el.querySelectorAll(".o_wslides_js_lesson_quiz_question");
        const lastQuestionEl = questionEls[questionEls.length - 1];
        if (lastQuestionEl) {
            this.insertContent(
                event.detail.newQuestionRenderedTemplate,
                lastQuestionEl,
                "afterend"
            );
        } else {
            this.insertContent(event.detail.newQuestionRenderedTemplate, this.el, "afterbegin");
        }
        this.data.questionCount++;
        event.detail.destroy();
        this.showAddButton = true;
    }

    /**
     * Replace the edited question by the new question and destroy
     * the QuestionForm.
     */
    onDisplayUpdatedQuestion(event) {
        const editedQuestionEl = this.editedQuestionEls[event.detail.questionId];
        if (!editedQuestionEl) {
            return;
        }
        this.insertContent(event.detail.newQuestionRenderedTemplate, editedQuestionEl, "afterend");
        editedQuestionEl.remove();
        delete this.editedQuestionEls[event.detail.questionId];
        event.detail.destroy();
    }

    insertContent(content, locationEl, position) {
        const parser = new DOMParser();
        const contentEls = parser.parseFromString(content, "text/html").body.children;
        if (contentEls.length == 0) {
            return;
        }
        this.insert(contentEls[0], locationEl, position);
        for (let i = 1; i < contentEls.length; i++) {
            this.insert(contentEls[i], contentEls[i - 1], "afterend");
        }
    }

    /**
     * If the user cancels the creation or update of a Question it resets the display
     * of the updated Question or it displays back the buttons.
     */
    onResetDisplay(event) {
        const editedQuestionEl = this.editedQuestionEls[event.detail.questionId];
        if (event.detail.update) {
            editedQuestionEl.classList.remove("d-none");
        } else {
            this.showAddButton = true;
        }
        event.detail.destroy();
    }

    /**
     * After deletion of a Question the display is refreshed with the removal of the Question
     * the reordering of all the remaining Questions and the change of the new Question sequence
     * if the QuestionFormWidget is initialized.
     */
    onDeleteQuestion(questionId) {
        this.el
            .querySelector(`.o_wslides_js_lesson_quiz_question[data-question-id="${questionId}"]`)
            .remove();
        this.data.questionCount--;
        this.reorderQuestions();
        if (
            this.data.questionCount === 0 &&
            !this.el.querySelector(".o_wsildes_quiz_question_input")
        ) {
            this.showValidationInfo = false;
        }
    }
}

class WebsiteSlidesQuizNoFullscreen extends WebsiteSlidesQuiz {
    static selector = ".o_wslides_js_lesson_quiz";
}

class WebsiteSlidesCoursePageQuiz extends WebsiteSlidesCoursePage {
    static selector = ".o_wslides_lesson_main";
    dynamicContent = {
        ...this.dynamicContent,
        ".o_wslides_js_lesson_quiz": {
            "t-on-slide_go_next": this.onQuizNextSlide,
        },
    };

    setup() {
        super.setup();
        this.data = this.services.slides_course_quiz.get();
    }

    onQuizNextSlide() {
        const url = this.el.querySelector(".o_wslides_js_lesson_quiz").dataset.nextSlideUrl;
        redirect(url);
    }

    /**
     * Get the slide data from the elements in the DOM.
     *
     * We need this overwrite because a documentation in non-fullscreen view
     * doesn't have the standard "done" button and so in that case the slide
     * data can not be retrieved.
     *
     * @override
     * @param {Integer} slideId
     */
    getSlide(slideId) {
        const slide = super.getSlide(...arguments);
        if (slide) {
            return slide;
        }
        // A quiz in a documentation on non fullscreen view
        return getDataFromEl(
            this.el.querySelector(`.o_wslides_js_lesson_quiz[data-id="${slideId}"]`)
        );
    }

    /**
     * After a slide has been marked as completed / uncompleted, update the state
     * of this widget and reload the slide if needed (e.g. to re-show the questions
     * of a quiz).
     *
     * @override
     * @param {Object} slide
     * @param {Boolean} completed
     */
    // TODO: fix this method (quiz does not contain fetchQuiz method)
    async toggleCompletionButton(slide, completed = true) {
        super.toggleCompletionButton(...arguments);
        // if (
        //     this.quiz &&
        //     this.quiz.slide.id === slide.id &&
        //     !completed &&
        //     this.quiz.quiz.questionCount
        // ) {
        //     // The quiz has been marked as "Not Done", re-load the questions
        //     this.quiz.quiz.answers = null;
        //     this.quiz.quiz.sessionAnswers = null;
        //     this.quiz.slide.completed = false;
        //     this.quiz._fetchQuiz().then(() => {
        //         this.quiz.renderElement();
        //         this.quiz._renderValidationInfo();
        //     });
        // }

        // // The quiz has been submitted in a documentation and in non fullscreen view,
        // // should update the button "Mark Done" to "Mark To Do"
        // const $doneButton = $(".o_wslides_done_button");
        // if ($doneButton.length && completed) {
        //     $doneButton
        //         .removeClass("o_wslides_done_button disabled btn-primary text-white")
        //         .addClass("o_wslides_undone_button btn-light")
        //         .text(_t("Mark To Do"))
        //         .removeAttr("title")
        //         .removeAttr("aria-disabled")
        //         .attr("href", `/slides/slide/${encodeURIComponent(slide.id)}/set_uncompleted`);
        // }
    }
}

// registry.category("public.interactions").add("website_slides.WebsiteSlidesQuiz", WebsiteSlidesQuiz);
registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesCoursePageQuiz", WebsiteSlidesCoursePageQuiz);
registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesQuizNoFullscreen", WebsiteSlidesQuizNoFullscreen);
