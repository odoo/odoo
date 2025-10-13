import { registerThreadAction } from "@mail/core/common/thread_actions";
import { PinnedMessagesPanel } from "@mail/discuss/message_pin/common/pinned_messages_panel";

import { useChildSubEnv } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

registerThreadAction("pinned-messages", {
    actionPanelComponent: PinnedMessagesPanel,
    actionPanelOuterClass: "o-discuss-PinnedMessagesPanel bg-inherit",
    condition: ({ channel, owner }) =>
        channel &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-thumb-tack",
    name: ({ action }) => (action.isActive ? _t("Hide Pinned Messages") : _t("Pinned Messages")),
    sequence: 20,
    sequenceGroup: 10,
    setup() {
        useChildSubEnv({
            pinMenu: {
                open: () => this.actionPanelOpen(),
                close: () => {
                    if (this.isActive) {
                        this.actionPanelClose();
                    }
                },
            },
        });
    },
});
