import { MessageSearchState } from "@mail/core/common/message_search_hook";
import { Component, t, useListener, useProps } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { SearchInput } from "@mail/core/common/search_input";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} SearchFilter
 * @property {string} label
 * @property {string} name
 * @property {string|undefined} [search_filter]
 */

export class SearchMessageInput extends Component {
    static template = "mail.SearchMessageInput";
    static components = { Dropdown, DropdownItem, SearchInput };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            closeSearch: t.function([]).optional(),
            messageSearch: t.instanceOf(MessageSearchState),
            thread: t.instanceOf(this.store["mail.thread"]),
        });
        useListener(
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

    /** @param {SearchFilter} searchFilter */
    onChangeSearchFilter(searchFilter) {
        if (searchFilter.search_filter !== this.props.messageSearch.search_filter) {
            this.props.messageSearch.lastEmptyTerm = undefined;
            this.props.messageSearch.search_filter = searchFilter.search_filter;
        }
    }

    /** @returns {SearchFilter[]} */
    get searchFilters() {
        return [
            { label: "all", name: _t("All"), search_filter: undefined },
            { label: "messages", name: _t("Messages"), search_filter: "messages" },
            { label: "notes", name: _t("Notes"), search_filter: "notes" },
            { label: "activities", name: _t("Activities"), search_filter: "activities" },
            { label: "changes", name: _t("Changes"), search_filter: "changes" },
        ];
    }

    get inputPlaceholder() {
        return _t("Search %(threadName)s", { threadName: this.props.thread.displayName });
    }
}
