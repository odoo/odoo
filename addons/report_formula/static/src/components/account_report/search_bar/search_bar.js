/** @odoo-module native */
import { Component, onMounted, useRef, useState } from "@odoo/owl";

export class AccountReportSearchBar extends Component {
    static template = "report_formula.AccountReportSearchBar";
    static props = {
        initialQuery: { type: String, optional: true },
    };

    setup() {
        this.searchText = useRef("search_bar_input");
        this.controller = useState(this.env.controller);

        onMounted(() => {
            if (this.props.initialQuery) {
                this.searchText.el.value = this.props.initialQuery;
                this.search();
            }
        });
    }

    //------------------------------------------------------------------------------------------------------------------
    // Search
    //------------------------------------------------------------------------------------------------------------------
    async search() {
        const inputText = this.searchText.el.value.trim();
        const query = inputText.toLowerCase();
        const linesIDsMatched = [];

        // Since the search bar is loaded before the report data, we need to wait for it
        await this.controller.reportLoadingPromise;

        if (query.length) {
            for (const line of this.controller.lines) {
                if (!line.name) {
                    continue;
                }

                const lineName = line.name.trim().toLowerCase();
                const match = lineName.indexOf(query) !== -1;

                if (match) {
                    linesIDsMatched.push(line.id);
                }
            }
            this.controller.lines_searched = linesIDsMatched;
            this.controller.updateOption("filter_search_bar", inputText);
        } else {
            delete this.controller.lines_searched;
            this.controller.deleteOption("filter_search_bar");
        }
    }
}
