/* @odoo-module */

import { MessageCardList } from "@mail/core/common/message_card_list";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

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
    static props = ["thread", "className?"];
    static template = "discuss.PinnedMessagesPanel";

    setup() {
        this.store = useService("mail.store");
        this.rpc = useService("rpc");
        this.messagePinService = useState(useService("discuss.message.pin"));
        onWillStart(() => {
            this.messagePinService.fetchPinnedMessages(this.props.thread);
        });
        onWillUpdateProps(async (nextProps) => {
            if (nextProps.thread.notEq(this.props.thread)) {
                this.messagePinService.fetchPinnedMessages(nextProps.thread);
            }
        });
    }

    /**
     * Prompt the user for confirmation and unpin the given message if
     * confirmed.
     *
     * @param {import('@mail/core/common/message_model').Message} message
     */
    onClickUnpin(message) {
        this.messagePinService.unpin(message);
    }

    /**
     * Get the message to display when nothing is pinned on this thread.
     */
    get emptyText() {
        if (this.props.thread.type === "channel") {
            return _t("This channel doesn't have any pinned messages.");
        } else {
            return _t("This conversation doesn't have any pinned messages.");
        }
    }

    get title() {
        return _t("Pinned Messages");
    }
}
