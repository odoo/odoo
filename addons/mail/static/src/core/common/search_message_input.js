import { Component, useExternalListener, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useAutofocus } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {function} [closeSearch]
 */

export class SearchMessageInput extends Component {
    static template = "mail.SearchMessageInput";
    static props = ["closeSearch?", "messageSearch", "thread"];
    static components = { Dropdown, DropdownItem };

    setup() {
        super.setup();
        this.state = useState({
            searchTerm: "",
            searchedTerm: "",
            searchType: this.env.inChatter ? "all_activity" : "",
        });
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
        this.props.messageSearch.searchType = this.state.searchType;
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

    setSearchType(searchType) {
        if (searchType !== this.state.searchType) {
            this.state.searchType = searchType;
        }
    }

    get searchTypes() {
        return [
            {
                name: _t("All Activity"),
                label: "all_activity",
            },
            {
                name: _t("Conversation"),
                label: "conversation",
            },
            {
                name: _t("Tracked Changes"),
                label: "tracked_changes",
            },
        ];
    }
}
