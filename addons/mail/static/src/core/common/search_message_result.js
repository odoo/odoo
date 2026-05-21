import { Component } from "@odoo/owl";
import { MessageCardList } from "./message_card_list";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {ReturnType<typeof import("@mail/core/common/message_search_hook").useMessageSearch>} messageSearch
 * @property {function} [onClickJump]
 */
export class SearchMessageResult extends Component {
    static template = "mail.SearchMessageResult";
    static components = { MessageCardList };
    static props = ["thread", "messageSearch", "onClickJump?"];

    get MESSAGE_FOUND() {
        if (this.props.messageSearch.messages.length === 0) {
            return false;
        }
        if (this.props.messageSearch.count === 1) {
            return _t("1 message found");
        }
        return _t("%s messages found", this.props.messageSearch.count);
    }

    onLoadMoreVisible() {
        const msgs = this.props.messageSearch.messages;
        if (!msgs?.length) {
            return;
        }
        this.props.messageSearch.loadMore(Math.min(...msgs.map((m) => m.id)));
    }
}
