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
        if (this.props.messageSearch.messages.length === 0) {
            return false;
        }
        return _t("%s messages found", this.props.messageSearch.count);
    }

    onLoadMoreVisible() {
        const before = this.props.messageSearch?.messages
            ? Math.min(...this.props.messageSearch.messages.map((message) => message.id))
            : false;
        this.props.messageSearch.search(before);
    }
}
