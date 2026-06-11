import { MessageCardList } from "@mail/core/common/message_card_list";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { useOnChange } from "@mail/utils/common/hooks";

import { Component, props, types } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class PinnedMessagesPanel extends Component {
    static components = {
        MessageCardList,
        ActionPanel,
    };
    static template = "discuss.PinnedMessagesPanel";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            channel: types.instanceOf(this.store["discuss.channel"].Class),
            "close?": types.function([types.instanceOf(MouseEvent)]),
        });
        useOnChange(
            () => this.props.channel.fetchPinnedMessages(),
            () => [this.props.channel]
        );
    }

    /**
     * Get the message to display when nothing is pinned on this channel.
     */
    get emptyText() {
        return _t("This channel doesn't have any pinned messages.");
    }
}
