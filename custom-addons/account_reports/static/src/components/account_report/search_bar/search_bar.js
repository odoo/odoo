/** @odoo-module */

import { Component, useRef, useState, onMounted } from "@odoo/owl";

export class AccountReportSearchBar extends Component {
    static template = "account_reports.AccountReportSearchBar";
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
    search() {
        const query = this.searchText.el.value.trim().toLowerCase();
        const linesIDsMatched = [];

        if (query.length) {
            for (const line of this.controller.lines) {
                const lineName = line.name.trim().toLowerCase();
                const match = (lineName.indexOf(query) !== -1);

                if (match) {
                    linesIDsMatched.push(line.id);
                }
            }
        }

        if (linesIDsMatched.length) {
            this.controller.lines_searched = linesIDsMatched;
            this.controller.updateOption("filter_search_bar", query);
        } else {
            delete this.controller.lines_searched;
            this.controller.deleteOption("filter_search_bar");
        }        
    }
}
