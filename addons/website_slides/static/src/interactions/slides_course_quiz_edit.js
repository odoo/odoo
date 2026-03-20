import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { insertHtmlContent } from "@website_slides/js/utils";
import { WebsiteSlidesCourseQuizQuestionForm } from "@website_slides/js/public/components/slides_course_quiz_question_form/slides_course_quiz_question_form";
import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";

export class WebsiteSlidesQuizEdit extends Interaction {
    static selector = ".o_wslides_js_lesson_quiz";
    dynamicContent = {
        ".o_wslides_js_quiz_add": { "t-on-click": this.onCreateQuestionClick },
        ".o_wslides_js_quiz_edit_question": { "t-on-click": this.onEditQuestionClick },
        ".o_wslides_js_quiz_delete_question": { "t-on-click": this.onDeleteQuestionClick },
        ".o_wslides_js_quiz_add_quiz": {
            "t-att-class": () => ({
                "d-none": !this.showAddButton || this.quiz.questionCount,
            }),
        },
        ".o_wslides_js_quiz_add_question": {
            "t-att-class": () => ({
                "d-none": !this.showAddButton || !this.quiz.questionCount,
            }),
        },
        ".o_wslides_js_lesson_quiz_question .o_wslides_js_quiz_edit_del,\
        .o_wslides_js_lesson_quiz_question .o_wslides_js_quiz_sequence_handler": {
            "t-att-class": () => ({ "d-none": !this.showEditOptions }),
        },
    };

    setup() {
        this.dialog = this.services.dialog;
        this.orm = this.services.orm;
        this.sortable = this.services.sortable;

        this.slidesService = this.services.website_slides;
        this.bus = this.slidesService.bus;
        this.quiz = this.slidesService.data.quiz;
        this.initServiceData();

        this.showAddButton = true;
        // TODO: Don't show edit options after submitting a quiz
        this.showEditOptions = true;
    }

    start() {
        this.checkLocationHref();
        this.bindSortable();
    }

    destroy() {
        this.unbindSortable();
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
        await this.waitFor(
            this.orm.webResequence("slide.question", this.getQuestionsIds(), { offset: 1 })
        );
        this.modifyQuestionsSequence();
    }

    /**
     * If the slides has been called with the Add Quiz button on the slide list
     * it goes straight to the 'Add Quiz' button and clicks on it.
     */
    checkLocationHref() {
        if (window.location.href.includes("quiz_quick_create") && !this.quiz.questionCount) {
            this.onCreateQuestionClick();
        }
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

    initServiceData() {
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
    }

    /**
     * When clicking on 'Add a Question' or 'Add Quiz' it
     * initialize a new QuestionForm to input the new
     * question.
     */
    onCreateQuestionClick() {
        const containerEl = this.el.querySelector(".o_wslides_js_lesson_quiz_new_question");
        this.showAddButton = false;
        const destroy = this.mountComponent(containerEl, WebsiteSlidesCourseQuizQuestionForm, {
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
                destroy();
                this.updateContent();
            },
            onCancel: () => {
                this.showAddButton = true;
                destroy();
                this.updateContent();
            },
        });
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
     * When clicking on the edit button of a question it
     * initializes a new QuestionForm component with the existing
     * question as input.
     */
    onEditQuestionClick(ev) {
        const editedQuestionEl = ev.currentTarget.closest(".o_wslides_js_lesson_quiz_question");
        const question = this.getQuestionDetails(editedQuestionEl);
        const destroy = this.mountComponent(
            editedQuestionEl,
            WebsiteSlidesCourseQuizQuestionForm,
            {
                question,
                update: true,
                onSave: (renderedQuestion) => {
                    insertHtmlContent(this, renderedQuestion, editedQuestionEl, "afterend");
                    editedQuestionEl.remove();
                    destroy();
                },
                onCancel: () => {
                    editedQuestionEl.classList.remove("d-none");
                    destroy();
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
    onDeleteQuestionClick(ev) {
        const question = ev.currentTarget.closest(".o_wslides_js_lesson_quiz_question");
        const questionId = parseInt(question.dataset.questionId);
        this.dialog.add(ConfirmationDialog, {
            title: _t("Delete Question"),
            body: _t('Are you sure you want to delete this question "%(title)s"?', {
                title: markup`<strong>${question.dataset.title}</strong>`,
            }),
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

registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesQuizEdit", WebsiteSlidesQuizEdit);
