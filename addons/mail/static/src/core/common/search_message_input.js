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
 * @property {string|undefined} id value sent as `search_filter` to `_message_fetch` (`undefined` = All)
 * @property {TranslatedString} name
 */

/**
 * Supported message search filters for `_message_fetch`.
 * Keep in sync with `MESSAGE_SEARCH_FILTERS` in `mail/models/mail_message.py`.
 *
 * @type {SearchFilter[]}
 */
export const MESSAGE_SEARCH_FILTERS = [
    { id: undefined, name: _t("All") },
    { id: "messages", name: _t("Messages") },
    { id: "notes", name: _t("Notes") },
    { id: "activities", name: _t("Activities") },
    { id: "changes", name: _t("Changes") },
];

export class SearchMessageInput extends Component {
    static template = "mail.SearchMessageInput";
    static components = { Dropdown, DropdownItem, SearchInput };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.MESSAGE_SEARCH_FILTERS = MESSAGE_SEARCH_FILTERS;
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
        if (searchFilter.id !== this.props.messageSearch.search_filter) {
            this.props.messageSearch.lastEmptyTerm = undefined;
            this.props.messageSearch.search_filter = searchFilter.id;
        }
    }

    get inputPlaceholder() {
        return _t("Search %(threadName)s", { threadName: this.props.thread.displayName });
    }
}
