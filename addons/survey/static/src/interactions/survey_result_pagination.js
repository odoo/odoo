import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

// TODO awa: this widget loads all records and only hides some based on page
// -> this is ugly / not efficient, needs to be refactored

export class SurveyResultPagination extends Interaction {
    static selector = ".pagination_wrapper";
    dynamicContent = {
        "li.o_survey_js_results_pagination a": {
            "t-on-click.prevent": this.onPageClick,
        },
        ".o_survey_question_answers_show_btn": {
            "t-on-click": this.onShowAllAnswers,
        },
    };

    setup() {
        this.questionId = this.el.dataset["question_id"];
        this.resultsTableEl = this.el.parentElement.querySelector(
            "#survey_table_question_" + this.questionId
        );
        this.pageBtnsEl = this.el.querySelector("ul.pagination");
        this.limit = this.el.dataset["record_limit"];
        this.elCount = this.resultsTableEl.querySelector("tbody").childElementCount;
        this.currentPage = 1;
    }

    onPageClick(ev) {
        this.pageBtnsEl
            .querySelector(`li:nth-child(${this.currentPage})`)
            .classList.remove("active");

        // Hide entries from the old page
        let min = this.limit * (this.currentPage - 1);
        let max = Math.min(this.elCount, this.limit * this.currentPage);
        for (let idx = min; idx < max; idx++) {
            this.resultsTableEl
                .querySelector(`tbody tr:nth-child(${idx + 1})`)
                .classList.add("d-none");
        }

        this.currentPage = ev.currentTarget.text;
        this.pageBtnsEl.querySelector(`li:nth-child(${this.currentPage})`).classList.add("active");

        // Show entries from the new page
        min = this.limit * (this.currentPage - 1);
        max = Math.min(this.elCount, this.limit * this.currentPage);
        for (let idx = min; idx < max; idx++) {
            this.resultsTableEl
                .querySelector(`tbody tr:nth-child(${idx + 1})`)
                .classList.remove("d-none");
        }
    }

    onShowAllAnswers(ev) {
        const btnEl = ev.currentTarget;
        const pager = btnEl.previousElementSibling;
        btnEl.classList.add("d-none");
        for (const tr of this.resultsTableEl.querySelectorAll("tbody tr")) {
            tr.classList.remove("d-none");
        }
        pager.classList.add("d-none");
        this.resultsTableEl.parentElement.classList.add("h-auto");
    }
}

registry
    .category("public.interactions")
    .add("survey.survey_result_pagination", SurveyResultPagination);
