import { Component, useState, onWillUpdateProps } from "@odoo/owl";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { SearchMessageInput } from "@mail/core/common/search_message_input";
import { SearchMessageResult } from "@mail/core/common/search_message_result";
import { useMessageSearch } from "./message_search_hook";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 */
export class SearchMessagesPanel extends Component {
    static template = "mail.SearchMessagesPanel";
    static components = { ActionPanel, SearchMessageInput, SearchMessageResult };
    static props = ["thread"];

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.messageSearch = useMessageSearch(this.props.thread);
        onWillUpdateProps((nextProps) => {
            if (this.props.thread.notEq(nextProps.thread)) {
                this.env.searchMenu?.close();
            }
        });
    }

    get title() {
        return _t("Search Message");
    }
}
