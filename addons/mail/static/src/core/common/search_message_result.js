import { Component, props, t } from "@odoo/owl";
import { MessageCardList } from "./message_card_list";
import { MessageSearchState } from "@mail/core/common/message_search_hook";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class SearchMessageResult extends Component {
    static template = "mail.SearchMessageResult";
    static components = { MessageCardList };

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = props({
            messageSearch: t.instanceOf(MessageSearchState),
            onClickJump: t.function([]).optional(),
            thread: t.instanceOf(this.store["mail.thread"].Class),
        });
    }

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
