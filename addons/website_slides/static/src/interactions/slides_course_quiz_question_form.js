import { Interaction } from "@web/public/interaction";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { getDataFromEl } from "@web/public/utils";
import { registry } from "@web/core/registry";

class WebsiteSlidesQuestionForm extends Interaction {
    static selector = ".o_wsildes_quiz_question_input";
    dynamicContent = {
        ".o_wslides_js_quiz_validate_question": { "t-on-click": this.onValidateQuestionClick },
        ".o_wslides_js_quiz_cancel_question": { "t-on-click": this.onCancelValidationClick },
        ".o_wslides_js_quiz_comment_answer": { "t-on-click": this.onToggleAnswerLineCommentClick },
        ".o_wslides_js_quiz_add_answer": { "t-on-click": this.onAddAnswerLineClick },
        ".o_wslides_js_quiz_remove_answer": { "t-on-click": this.onRemoveAnswerLineClick },
        ".o_wslides_js_quiz_remove_answer_comment": {
            "t-on-click": this.onRemoveAnswerLineCommentClick,
        },
        ".o_wslides_js_quiz_answer_comment > input[type=text]": {
            "t-on-change": this.onCommentChange,
        },
        ".o_wslides_js_quiz_validation_error": {
            "t-att-class": () => ({ "d-none": !this.error }),
        },
        ".o_wslides_js_quiz_validation_error_text": {
            "t-out": () => this.error || "",
        },
    };

    setup() {
        this.quizService = this.services.slides_course_quiz;
        this.data = this.quizService.get();
        const data = getDataFromEl(this.el);
        this.update = data.update;
        if (this.update) {
            this.question = this.data.currentlyEditedQuestions[data.questionId];
        } else {
            this.question = {};
        }
        this.el.querySelector(".o_wslides_quiz_question input").focus();
        this.error = null;
    }

    onCommentChange(event) {
        const inputEl = event.currentTarget;
        const commentIconEl = inputEl
            .closest(".o_wslides_js_quiz_answer")
            .querySelector(".o_wslides_js_quiz_comment_answer");
        if (inputEl.value.trim() !== "") {
            commentIconEl.classList.add("text-primary");
            commentIconEl.classList.remove("text-muted");
        } else {
            commentIconEl.classList.add("text-muted");
            commentIconEl.classList.remove("text-primary");
        }
    }

    /**
     * Toggle the input for commenting the answer line which will be
     * seen by the frontend user when submitting the quiz.
     */
    onToggleAnswerLineCommentClick(event) {
        const commentLineEl = event.currentTarget
            .closest(".o_wslides_js_quiz_answer")
            .querySelector(".o_wslides_js_quiz_answer_comment")
            .classList.toggle("d-none");
        commentLineEl.querySelector("input[type=text]").focus();
    }

    /**
     * Adds a new answer line after the element the user clicked on
     * e.g. If there is 3 answer lines and the user click on the add
     *      answer button on the second line, the new answer line will
     *      display between the second and the third line.
     */
    onAddAnswerLineClick(event) {
        this.renderAt(
            "slide.quiz.answer.line",
            {},
            event.currentTarget.closest(".o_wslides_js_quiz_answer"),
            "afterend"
        );
    }

    /**
     * Removes an answer line. Can't remove the last answer line.
     */
    onRemoveAnswerLineClick(event) {
        if (this.el.querySelector(".o_wslides_js_quiz_answer")) {
            event.currentTarget.closest(".o_wslides_js_quiz_answer").remove();
        }
    }

    onRemoveAnswerLineCommentClick(event) {
        const commentLineEl = event.currentTarget
            .closest(".o_wslides_js_quiz_answer_comment")
            .classList.add("d-none");
        const inputEl = commentLineEl.querySelector("input[type=text]");
        inputEl.value = "";
        inputEl.dispatchEvent(new Event("change"));
    }

    /**
     * Handler when user click on 'Save' or 'Update' buttons.
     */
    onValidateQuestionClick(event) {
        this.createOrUpdateQuestion({
            update: event.currentTarget.classList.contains("o_wslides_js_quiz_update"),
        });
    }

    /**
     * Handler when user click on the 'Cancel' button.
     * Calls a method from slides_course_quiz.js widget
     * which will handle the reset of the question display.
     */
    onCancelValidationClick() {
        this.el.dispatchEvent(
            new CustomEvent("reset_display", {
                detail: {
                    update: this.update,
                    questionId: this.question.id,
                    destroy: () => this.el.remove(),
                },
            })
        );
    }

    /**
     * RPC call to create or update a question.
     * Triggers method from slides_course_quiz.js to
     * correctly display the question.
     */
    async createOrUpdateQuestion(options) {
        const formEl = this.el.querySelector("form");
        if (this.isValidForm(formEl)) {
            const values = this.serializeForm(formEl);
            const renderedQuestion = await this.waitFor(
                rpc("/slides/slide/quiz/question_add_or_update", values)
            );
            if (typeof renderedQuestion === "object" && renderedQuestion.error) {
                this.error = renderedQuestion.error;
            } else if (options.update) {
                this.error = null;
                this.quizService.endUpdatingQuestion(this.question);
                this.el.dispatchEvent(
                    new CustomEvent("display_updated_question", {
                        detail: {
                            newQuestionRenderedTemplate: renderedQuestion,
                            questionId: this.question.id,
                            destroy: () => this.el.remove(),
                        },
                    })
                );
            } else {
                this.error = null;
                this.quizService.endUpdatingQuestion(this.question);
                this.el.dispatchEvent(
                    new CustomEvent("display_created_question", {
                        detail: {
                            newQuestionRenderedTemplate: renderedQuestion,
                            destroy: () => this.el.remove(),
                        },
                    })
                );
            }
        } else {
            this.error = _t("Please fill in the question");
            this.el.querySelector(".o_wslides_quiz_question input").focus();
        }
        this.updateContent();
    }

    /**
     * Check if the Question has been filled up
     */
    isValidForm(formEl) {
        return (
            formEl.querySelector(".o_wslides_quiz_question input[type=text]").value.trim() !== ""
        );
    }

    /**
     * Serialize the form into a JSON object to send it
     * to the server through a RPC call.
     * @returns {{id: *, sequence: *, question: *, slide_id: *, answer_ids: Array}}
     */
    serializeForm(formEl) {
        const answers = [];
        let sequence = 1;
        for (const answerEl of formEl.querySelectorAll(".o_wslides_js_quiz_answer")) {
            const value = answerEl.querySelector(".o_wslides_js_quiz_answer_value").value;
            if (value.trim() !== "") {
                const answer = {
                    sequence: sequence++,
                    text_value: value,
                    is_correct: answerEl.querySelector("input[type=radio]").checked,
                    comment: answerEl
                        .querySelector(".o_wslides_js_quiz_answer_comment input[type=text]")
                        .value.trim(),
                };
                answers.push(answer);
            }
        }
        return {
            existing_question_id: this.question.id,
            sequence: parseInt(
                this.el.querySelector(".o_wslides_quiz_question_sequence").textContent
            ),
            question: formEl.querySelector(".o_wslides_quiz_question input[type=text]").value,
            slide_id: this.data.id,
            answer_ids: answers,
        };
    }
}

registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesQuestionForm", WebsiteSlidesQuestionForm);
