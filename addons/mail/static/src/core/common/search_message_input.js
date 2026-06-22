import { MessageSearchState } from "@mail/core/common/message_search_hook";
import { Component, props, t, useListener } from "@odoo/owl";
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
 * @property {true|false|undefined} [is_notification]
 */

export class SearchMessageInput extends Component {
    static template = "mail.SearchMessageInput";
    static components = { Dropdown, DropdownItem, SearchInput };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            closeSearch: t.function([]).optional(),
            messageSearch: t.instanceOf(MessageSearchState),
            thread: t.instanceOf(this.store["mail.thread"].Class),
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
        if (searchFilter.is_notification !== this.props.messageSearch.is_notification) {
            this.props.messageSearch.is_notification = searchFilter.is_notification;
        }
    }

    /** @returns {SearchFilter[]} */
    get searchFilters() {
        return [
            { label: "all", name: _t("All"), is_notification: undefined },
            { label: "conversations", name: _t("Conversations"), is_notification: false },
            { label: "tracked_changes", name: _t("Tracked Changes"), is_notification: true },
        ];
    }

    get inputPlaceholder() {
        return _t("Search %(threadName)s", { threadName: this.props.thread.displayName });
    }
}
