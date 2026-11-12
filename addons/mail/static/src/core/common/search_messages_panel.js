import { MessageSearchPlugin } from "@mail/core/common/message_search_plugin";
import { Component, providePlugins, t, useOnChange, usePlugin, useProps } from "@odoo/owl";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { SearchMessageInput } from "@mail/core/common/search_message_input";
import { SearchMessageResult } from "@mail/core/common/search_message_result";

export class SearchMessagesPanel extends Component {
    static template = "mail.SearchMessagesPanel";
    static components = { ActionPanel, SearchMessageInput, SearchMessageResult };

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            close: t.function([]).optional(),
            thread: t.instanceOf(this.store["mail.thread"]),
        });
        providePlugins([MessageSearchPlugin], { thread: () => this.props.thread });
        this.messageSearch = usePlugin(MessageSearchPlugin);
        useOnChange(
            () => [this.props.thread],
            () => this.props.close?.(),
            { initialRun: false }
        );
    }

    get title() {
        return _t("Search Messages");
    }
}
