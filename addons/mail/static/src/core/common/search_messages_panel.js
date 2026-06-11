import { Component, props, t } from "@odoo/owl";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { SearchMessageInput } from "@mail/core/common/search_message_input";
import { SearchMessageResult } from "@mail/core/common/search_message_result";
import { useMessageSearch } from "./message_search_hook";
import { useOnChange } from "@mail/utils/common/hooks";

export class SearchMessagesPanel extends Component {
    static template = "mail.SearchMessagesPanel";
    static components = { ActionPanel, SearchMessageInput, SearchMessageResult };

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = props({
            close: t.function([]).optional(),
            thread: t.instanceOf(this.store["mail.thread"].Class),
        });
        this.messageSearch = this.env.messageSearch ?? useMessageSearch(this.props.thread);
        useOnChange(
            () => [this.props.thread],
            () => this.env.searchMenu?.close(),
            { initialRun: false }
        );
    }

    get title() {
        return _t("Search Messages");
    }
}
