import { Component, useEffect, useState, useRef } from "@odoo/owl";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

export class WebsiteSlidesCourseQuizQuestionForm extends Component {
    static template = "slide.quiz.question.input";
    static props = {
        update: Boolean,
        question: Object,
        onSave: Function,
        onCancel: Function,
    };

    setup() {
        this.slidesService = useService("website_slides");
        this.slide = this.slidesService.data.slide;
        this.bus = this.slidesService.bus;
        this.state = useState({
            answerLines: [],
            error: null,
        });
        if (this.props.update) {
            this.question = this.props.question;
            for (const answer of this.question.answers) {
                this.state.answerLines.push({
                    id: answer.id,
                    text: answer.text_value,
                    isCorrect: answer.is_correct,
                    comment: answer.comment,
                    placeholder: "",
                });
            }
        } else {
            this.question = {};
            this.state.answerLines = [
                { id: 1, placeholder: "A giraffe", text: "", isCorrect: false, comment: "" },
                { id: 2, placeholder: "A bird", text: "", isCorrect: false, comment: "" },
                { id: 3, placeholder: "A fly", text: "", isCorrect: false, comment: "" },
            ];
        }

        this.inputRef = useAutofocus({ refName: "input" });
        this.formRef = useRef("form");
        this.sequenceRef = useRef("sequence");

        useEffect(
            (update) => {
                if (!update) {
                    return;
                }
                const questionsReorderHandler = this.onQuestionsReordered.bind(this);
                this.bus.addEventListener("questions_reordered", questionsReorderHandler);
                return () => {
                    this.bus.removeEventListener("questions_reordered", questionsReorderHandler);
                };
            },
            () => [this.props.update]
        );
    }

    onQuestionsReordered() {
        this.props.question.sequence = parseInt(this.sequenceRef.el.textContent);
    }

    onIsCorrectClick(answer, isCorrect) {
        for (const answer of this.state.answerLines) {
            answer.isCorrect = false;
        }
        answer.isCorrect = isCorrect;
    }

    /**
     * Toggle the input for commenting the answer line which will be
     * seen by the frontend user when submitting the quiz.
     */
    onToggleAnswerLineCommentClick(event) {
        const commentLineEl = event.currentTarget
            .closest(".o_wslides_js_quiz_answer")
            .querySelector(".o_wslides_js_quiz_answer_comment");
        commentLineEl.classList.toggle("d-none");
        commentLineEl.querySelector("input[type=text]").focus();
    }

    /**
     * Adds a new answer line after the element the user clicked on
     * e.g. If there is 3 answer lines and the user click on the add
     *      answer button on the second line, the new answer line will
     *      display between the second and the third line.
     */
    onAddAnswerLineClick(beforeAnswer) {
        const answerLines = [];
        for (const answer of this.state.answerLines) {
            answerLines.push(answer);
            if (answer.id === beforeAnswer.id) {
                answerLines.push({
                    id: this.state.answerLines.length + 1,
                    text: "",
                    comment: "",
                    isCorrect: false,
                });
            }
        }
        this.state.answerLines = answerLines;
    }

    /**
     * Removes an answer line. Can't remove the last answer line.
     */
    onRemoveAnswerLineClick(answer) {
        this.state.answerLines = this.state.answerLines.filter((value) => value.id !== answer.id);
    }

    onRemoveAnswerLineCommentClick(event, answer) {
        const commentLineEl = event.currentTarget.closest(".o_wslides_js_quiz_answer_comment");
        commentLineEl.classList.add("d-none");
        answer.comment = "";
    }

    /**
     * Handler when user click on 'Save' or 'Update' buttons.
     */
    async onValidateQuestionClick() {
        if (this.isValidForm(this.formRef.el)) {
            const values = this.serializeForm(this.formRef.el);
            const renderedQuestion = await rpc("/slides/slide/quiz/question_add_or_update", values);
            if (typeof renderedQuestion === "object" && renderedQuestion.error) {
                this.state.error = renderedQuestion.error;
            } else {
                this.state.error = null;
                this.props.onSave(renderedQuestion);
            }
        } else {
            this.state.error = _t("Please fill in the question");
            this.inputRef.el.focus();
        }
    }

    onCancelValidationClick() {
        this.props.onCancel();
    }

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
            if (value.trim()) {
                answers.push({
                    sequence: sequence++,
                    text_value: value,
                    is_correct: answerEl.querySelector("input[type=radio]").checked,
                    comment: answerEl
                        .querySelector(".o_wslides_js_quiz_answer_comment input[type=text]")
                        .value.trim(),
                });
            }
        }
        return {
            existing_question_id: this.question.id,
            sequence: this.props.question.sequence,
            question: this.props.question.text,
            slide_id: this.slide.id,
            answer_ids: answers,
        };
    }
}
