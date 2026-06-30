import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { renderToMarkup } from "@web/core/utils/render";

export class SurveyResultPagination extends Interaction {
    static selector = ".survey_table_with_pagination";
    dynamicContent = {
        "li.o_survey_js_results_pagination a": {
            "t-on-click.prevent": this.onPageClick,
        },
        ".o_survey_question_answers_show_btn": {
            "t-on-click": this.onShowAllAnswers,
            "t-att-class": () => ({
                "d-none": this.paginationState.showAll,
            }),
        },
        ".pagination": {
            "t-att-class": () => ({
                "d-none": this.paginationState.showAll,
            }),
        },
        ".o_survey_results_table_wrapper": {
            "t-att-class": () => ({
                "h-auto": this.paginationState.showAll,
            }),
        },
        tbody: {
            "t-out": () => this.tableContent,
        },
    };

    setup() {
        this.limit = this.el.dataset.record_limit;
        this.questionData = this.parseAnswersJSON();
        this.elCount = this.questionData.length;
        this.paginationState = {
            currentPage: 1,
            minIdx: 0,
            maxIdx: Math.min(this.elCount, this.limit),
            showAll: false,
            hideFilter: this.el.dataset.hideFilter,
        };

        // The following two events are dispatched by survey_result when user
        // clicks on the "print" button.
        this.el.addEventListener("save_state_and_show_all", () => {
            this.paginationStateBackup = Object.assign({}, this.paginationState);
            this.onShowAllAnswers();
            this.updateContent();
        });
        this.el.addEventListener("restore_state", () => {
            if (this.paginationStateBackup) {
                this.paginationState = this.paginationStateBackup;
            }
            this.updateContent();
        });
    }

    parseAnswersJSON() {
        const keys = ["id", "value", "url"];
        return JSON.parse(this.el.dataset.answersJson).map((entry, index) => {
            const content = Object.fromEntries(entry.map((value, index) => [keys[index], value]));
            return { index: index, ...content };
        });
    }

    get tableContent() {
        return renderToMarkup("survey.paginated_results_rows", {
            records: this.questionData.slice(
                this.paginationState.minIdx,
                this.paginationState.maxIdx
            ),
            hide_filter: this.paginationState.hideFilter,
        });
    }

    onPageClick(ev) {
        this.pageBtnsEl = this.el.querySelector("ul.pagination");
        this.pageBtnsEl
            .querySelector(`li:nth-child(${this.paginationState.currentPage})`)
            .classList.remove("active");
        this.paginationState.currentPage = ev.currentTarget.text;
        this.pageBtnsEl
            .querySelector(`li:nth-child(${this.paginationState.currentPage})`)
            .classList.add("active");
        this.paginationState.minIdx = this.limit * (this.paginationState.currentPage - 1);
        this.paginationState.maxIdx = Math.min(
            this.elCount,
            this.limit * this.paginationState.currentPage
        );
    }

    onShowAllAnswers() {
        this.paginationState.showAll = true;
        this.paginationState.minIdx = 0;
        this.paginationState.maxIdx = this.elCount;
    }
}

registry
    .category("public.interactions")
    .add("survey.survey_result_pagination", SurveyResultPagination);
