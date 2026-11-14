import { Component, t, usePlugin, useProps } from "@odoo/owl";
import { MessageCardList } from "./message_card_list";
import { MessageSearchPlugin } from "@mail/core/common/message_search_plugin";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class SearchMessageResult extends Component {
    static template = "mail.SearchMessageResult";
    static components = { MessageCardList };

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.messageSearch = usePlugin(MessageSearchPlugin);
        this.props = useProps({
            onClickJump: t.function([]).optional(),
            thread: t.instanceOf(this.store["mail.thread"]),
        });
    }

    get MESSAGE_FOUND() {
        if (this.messageSearch.messages().length === 0) {
            return false;
        }
        if (this.messageSearch.count() === 1) {
            return _t("1 message found");
        }
        return _t("%s messages found", this.messageSearch.count());
    }

    onLoadMoreVisible() {
        const msgs = this.messageSearch.messages();
        if (!msgs?.length) {
            return;
        }
        this.messageSearch.loadMore(Math.min(...msgs.map((m) => m.id)));
    }
}
