import { Component, t, useProps } from "@odoo/owl";
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
        this.props = useProps({
            messageSearch: t.instanceOf(MessageSearchState),
            onClickJump: t.function([]).optional(),
            thread: t.instanceOf(this.store["mail.thread"]),
        });
    }

    get MESSAGE_FOUND() {
        const count = this.props.messageSearch.messages.length;
        if (count === 0) {
            return false;
        }
        if (count === 1) {
            return _t("1 message found");
        }
        if (this.props.messageSearch.hasMore) {
            return _t(
                "Showing the first %s messages found. Narrow your search or scroll to see more.",
                count
            );
        }
        return _t("%s messages found", count);
    }

    onLoadMoreVisible() {
        const msgs = this.props.messageSearch.messages;
        if (!msgs?.length) {
            return;
        }
        this.props.messageSearch.loadMore(Math.min(...msgs.map((m) => m.id)));
    }
}
