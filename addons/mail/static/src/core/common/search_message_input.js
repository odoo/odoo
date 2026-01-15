import { Component, useExternalListener, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useAutofocus } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} SearchFilter
 * @property {string} label
 * @property {string} name
 * @property {true|false|undefined} [is_notification]
 */

/**
 * @typedef {Object} Props
 * @property {ReturnType<typeof import("@mail/core/common/message_search_hook").useMessageSearch>} messageSearch
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {function} [closeSearch]
 * @extends {Component<Props, Env>}
 */
export class SearchMessageInput extends Component {
    static template = "mail.SearchMessageInput";
    static props = ["closeSearch?", "messageSearch", "thread"];
    static components = { Dropdown, DropdownItem };

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

    /** @param {SearchFilter} searchFilter */
    onChangeSearchFilter(searchFilter) {
        if (searchFilter.is_notification !== this.props.messageSearch.is_notification) {
            this.props.messageSearch.is_notification = searchFilter.is_notification;
            if (this.state.searchTerm) {
                this.search();
            }
        }
    }

    /** @returns {SearchFilter[]} */
    get searchFilters() {
        return [
            {
                label: "all",
                name: _t("All"),
                is_notification: undefined,
            },
            {
                label: "conversations",
                name: _t("Conversations"),
                is_notification: false,
            },
            {
                label: "tracked_changes",
                name: _t("Tracked Changes"),
                is_notification: true,
            },
        ];
    }
}
