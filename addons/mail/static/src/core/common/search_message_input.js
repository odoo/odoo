import { Component, useExternalListener, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useAutofocus } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {function} [closeSearch]
 */

export class SearchMessageInput extends Component {
    static template = "mail.SearchMessageInput";
    static props = ["closeSearch?", "messageSearch", "thread"];

    setup() {
        super.setup();
        this.state = useState({ searchTerm: "", searchedTerm: "" });
        useAutofocus();
        useExternalListener(
            browser,
            "keydown",
            (ev) => {
                if (ev.key === "Escape") {
                    this.props.closeSearch?.();
                }
            },
            { capture: true }
        );
    }

    search() {
        this.props.messageSearch.searchTerm = this.state.searchTerm;
        this.props.messageSearch.search();
        this.state.searchedTerm = this.state.searchTerm;
    }

    clear() {
        this.state.searchTerm = "";
        this.state.searchedTerm = this.state.searchTerm;
        this.props.messageSearch.clear();
        this.props.closeSearch?.();
    }

    onKeydownSearch(ev) {
        if (ev.key !== "Enter") {
            return;
        }
        if (!this.state.searchTerm) {
            this.clear();
        } else {
            this.search();
        }
    }
}
