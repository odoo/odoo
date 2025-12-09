import { MessageCardList } from "@mail/core/common/message_card_list";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {string} [className]
 * @extends {Component<Props, Env>}
 */
export class PinnedMessagesPanel extends Component {
    static components = {
        MessageCardList,
        ActionPanel,
    };
    static props = ["channel", "className?"];
    static template = "discuss.PinnedMessagesPanel";

    setup() {
        super.setup();
        onWillStart(() => {
            this.props.channel.fetchPinnedMessages();
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.channel.notEq(this.props.channel)) {
                nextProps.channel.fetchPinnedMessages();
            }
        });
    }

    /**
     * Get the message to display when nothing is pinned on this channel.
     */
    get emptyText() {
        return _t("This channel doesn't have any pinned messages.");
    }
}
