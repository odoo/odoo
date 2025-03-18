import { SurveyImageZoomer } from "@survey/js/survey_image_zoomer";
import publicWidget from "@web/legacy/js/public/public_widget";
import { redirect } from "@web/core/utils/urls";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

publicWidget.registry.SurveyResultWidget = publicWidget.Widget.extend({
    selector: '.o_survey_result',
    events: {
        'click .o_survey_results_topbar_clear_filters': 'onClearFiltersClick',
        'click .filter-add-answer': 'onFilterAddAnswerClick',
        'click i.filter-remove-answer': 'onFilterRemoveAnswerClick',
        'click a.filter-finished-or-not': 'onFilterFinishedOrNotClick',
        'click a.filter-finished': 'onFilterFinishedClick',
        'click a.filter-failed': 'onFilterFailedClick',
        'click a.filter-passed': 'onFilterPassedClick',
        'click a.filter-passed-and-failed': 'onFilterPassedAndFailedClick',
        'click .o_survey_answer_image': 'onAnswerImageClick',
        "click .o_survey_results_print": "onPrintResultsClick",
        "click .o_survey_results_data_tab": "onDataViewChange",
    },

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
    * @override
    */
    async start() {
        await this._super.apply(this, arguments);

        // Set the size of results tables so that they do not resize when switching pages.
        document.querySelectorAll(".o_survey_results_table_wrapper").forEach((table) => {
            table.style.height = table.clientHeight + "px";
        });

        $(document).on("keydown", this.onKeydown.bind(this));
        return Promise.resolve();
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Recompute the table height as the table could have been hidden when its height was initially computed (see 'start').
     * @param {Event} ev
     */
    onDataViewChange(ev) {
        const tableWrapper = document.querySelector(`div[id="${ev.currentTarget.getAttribute('aria-controls')}"] .o_survey_results_table_wrapper`);
        if (tableWrapper) {
            tableWrapper.style.height = 'auto';
            tableWrapper.style.height = tableWrapper.clientHeight + 'px';
        }
    },

    /**
     * Add an answer filter by updating the URL and redirecting.
     * @param {Event} ev
     */
    onFilterAddAnswerClick(ev) {
        const params = new URLSearchParams(window.location.search);
        params.set("filters", this.prepareAnswersFilters(params.get("filters"), "add", ev));
        redirect(window.location.pathname + "?" + params.toString());
    },

    /**
     * Remove an answer filter by updating the URL and redirecting.
     * @param {Event} ev
     */
    onFilterRemoveAnswerClick(ev) {
        const params = new URLSearchParams(window.location.search);
        const filters = this.prepareAnswersFilters(params.get("filters"), "remove", ev);
        if (filters) {
            params.set("filters", filters);
        } else {
            params.delete("filters");
        }
        redirect(window.location.pathname + "?" + params.toString());
    },

    onClearFiltersClick() {
        const params = new URLSearchParams(window.location.search);
        params.delete("filters");
        params.delete("finished");
        params.delete("failed");
        params.delete("passed");
        redirect(window.location.pathname + "?" + params.toString());
    },

    onFilterFinishedOrNotClick() {
        const params = new URLSearchParams(window.location.search);
        params.delete("finished");
        redirect(window.location.pathname + "?" + params.toString());
    },

    onFilterFinishedClick() {
        const params = new URLSearchParams(window.location.search);
        params.set("finished", "true");
        redirect(window.location.pathname + "?" + params.toString());
    },

    onFilterFailedClick() {
        const params = new URLSearchParams(window.location.search);
        params.set("failed", "true");
        params.delete("passed");
        redirect(window.location.pathname + "?" + params.toString());
    },

    onFilterPassedClick() {
        const params = new URLSearchParams(window.location.search);
        params.set("passed", "true");
        params.delete("failed");
        redirect(window.location.pathname + "?" + params.toString());
    },

    onFilterPassedAndFailedClick() {
        const params = new URLSearchParams(window.location.search);
        params.delete("failed");
        params.delete("passed");
        redirect(window.location.pathname + "?" + params.toString());
    },

    /**
     * Called when an image on an answer in multi-answers question is clicked.
     * Starts a widget opening a dialog to display the now zoomable image.
     * this.imgZoomer is the zoomer widget linked to the survey result widget, if any.
     *
     * @param {Event} ev
     */
    onAnswerImageClick(ev) {
        ev.preventDefault();
        new SurveyImageZoomer({
            sourceImage: $(ev.currentTarget).attr('src')
        }).appendTo(document.body);
    },

    /**
     * Call print dialog
     */
    onPrintResultsClick() {
        // For each paginator, save the current state and uncollapse the table.
        for (const paginatorEl of document.querySelectorAll(".survey_table_with_pagination")) {
            paginatorEl.dispatchEvent(new Event("save_state_and_show_all"));
        }
        window.print();
        // Restore the original state of each paginator after the print.
        for (const paginatorEl of document.querySelectorAll(".survey_table_with_pagination")) {
            paginatorEl.dispatchEvent(new Event("restore_state"));
        }
    },

    /**
     * Called when a key is pressed on the survey result page.
     * If the user pressed CTRL+P, the print procedure is started.
     * @param {Event} ev Keydown event
     */
    onKeydown(ev) {
        if (getActiveHotkey(ev) === "control+p") {
            ev.preventDefault();
            ev.stopImmediatePropagation();
            this.onPrintResultsClick();
        }
    },

    /**
     * Returns the modified pathname string for filters after adding or removing an
     * answer filter (from click event).
     * @param {String} filters Existing answer filters, formatted as
     * `modelX,rowX,ansX|modelY,rowY,ansY...` - row is used for matrix-type questions row id, 0 for others
     * "model" specifying the model to query depending on the question type we filter on.
       - 'A': 'survey.question.answer' ids: simple_choice, multiple_choice, matrix
       - 'L': 'survey.user_input.line' ids: char_box, text_box, numerical_box, date, datetime
     * @param {"add" | "remove"} operation Whether to add or remove the filter.
     * @param {Event} ev Event defining the filter.
     * @returns {String} Updated filters.
     */
    prepareAnswersFilters(filters, operation, ev) {
        const cellDataset = ev.currentTarget.dataset;
        const filter = `${cellDataset.modelShortKey},${cellDataset.rowId || 0},${cellDataset.recordId}`;

        if (operation === "add") {
            if (filters) {
                filters = !filters.split("|").includes(filter) ? (filters += `|${filter}`) : filters;
            } else {
                filters = filter;
            }
        } else if (operation === "remove") {
            filters = filters
                .split("|")
                .filter((filterItem) => filterItem !== filter)
                .join("|");
        } else {
            throw new Error('`operation` parameter for `prepareAnswersFilters` must be either "add" or "remove".');
        }
        return filters;
    }
});

export default {
    resultWidget: publicWidget.registry.SurveyResultWidget,
};
