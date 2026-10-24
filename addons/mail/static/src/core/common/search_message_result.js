import { Component } from "@odoo/owl";
import { MessageCardList } from "./message_card_list";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {Object} [messaageSearch]
 * @property {function} [onClickJump]
 * @property {function} [loadMore]
 */
export class SearchMessageResult extends Component {
    static template = "mail.SearchMessageResult";
    static components = { MessageCardList };
    static props = ["thread", "messageSearch", "onClickJump?"];

    get MESSAGE_FOUND() {
        const count = this.props.messageSearch.messages.length;
        if (count === 0) {
            return false;
        }
        if (count === 1) {
            return _t("1 message found");
        }
        if (this.props.messageSearch.loadMore) {
            return _t(
                "Showing the first %(counter)s messages found. Narrow your search or scroll to see more.",
                { counter: count }
            );
        }
        return _t("%(counter)s messages found", { counter: count });
    }

    onLoadMoreVisible() {
        const before = this.props.messageSearch?.messages
            ? Math.min(...this.props.messageSearch.messages.map((message) => message.id))
            : false;
        this.props.messageSearch.search(before);
    }
}
