import { MessageCardList } from "@mail/core/common/message_card_list";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

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
        this.offlineService = useService("offline");
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
     * Get the message to display when nothing is pinned on this channel or client is offline.
     */
    get emptyText() {
        if (
            this.offlineService.status.offline &&
            this.props.channel.pinnedMessagesState !== "loaded"
        ) {
            return _t("Go online to load pinned messages.");
        }
        return _t("This channel doesn't have any pinned messages.");
    }
}
