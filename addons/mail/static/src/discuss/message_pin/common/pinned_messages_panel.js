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
    static props = ["thread", "className?"];
    static template = "discuss.PinnedMessagesPanel";

    setup() {
        super.setup();
        onWillStart(() => {
            this.props.thread.fetchPinnedMessages();
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.thread.notEq(this.props.thread)) {
                nextProps.thread.fetchPinnedMessages();
            }
        });
    }

    /**
     * Get the message to display when nothing is pinned on this thread.
     */
    get emptyText() {
        if (this.props.thread.channel_type === "channel") {
            return _t("This channel doesn't have any pinned messages.");
        } else {
            return _t("This conversation doesn't have any pinned messages.");
        }
    }
}
