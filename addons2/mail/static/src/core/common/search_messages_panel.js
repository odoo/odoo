/* @odoo-module */

import { Component, onWillUpdateProps, useExternalListener, useState } from "@odoo/owl";
import { useAutofocus } from "@web/core/utils/hooks";
import { useMessageSearch } from "@mail/core/common/message_search_hook";
import { browser } from "@web/core/browser/browser";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { MessageCardList } from "./message_card_list";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {string} [className]
 * @property {funtion} [closeSearch]
 * @property {funtion} [onClickJump]
 * @extends {Component<Props, Env>}
 */
export class SearchMessagesPanel extends Component {
    static components = {
        MessageCardList,
        ActionPanel,
    };
    static props = ["thread", "className?", "closeSearch?", "onClickJump?"];
    static template = "mail.SearchMessagesPanel";

    setup() {
        this.state = useState({ searchTerm: "", searchedTerm: "" });
        this.messageSearch = useMessageSearch(this.props.thread);
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
        onWillUpdateProps((nextProps) => {
            if (this.props.thread.notEq(nextProps.thread)) {
                this.env.searchMenu?.close();
            }
        });
    }

    get title() {
        return _t("Search messages");
    }

    get MESSAGES_FOUND() {
        if (this.messageSearch.messages.length === 0) {
            return false;
        }
        return _t("%s messages found", this.messageSearch.count);
    }

    search() {
        this.messageSearch.searchTerm = this.state.searchTerm;
        this.messageSearch.search();
        this.state.searchedTerm = this.state.searchTerm;
    }

    clear() {
        this.state.searchTerm = "";
        this.state.searchedTerm = this.state.searchTerm;
        this.messageSearch.clear();
        this.props.closeSearch?.();
    }

    /** @param {KeyboardEvent} ev */
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

    onLoadMoreVisible() {
        const before = this.messageSearch.messages
            ? Math.min(...this.messageSearch.messages.map((message) => message.id))
            : false;
        this.messageSearch.search(before);
    }
}
