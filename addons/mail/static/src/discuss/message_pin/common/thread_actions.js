import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { PinnedMessagesPanel } from "@mail/discuss/message_pin/common/pinned_messages_panel";

import { useChildSubEnv } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

threadActionsRegistry.add("pinned-messages", {
    component: PinnedMessagesPanel,
    condition(component) {
        return (
            component.thread?.model === "discuss.channel" &&
            (!component.props.chatWindow || component.props.chatWindow.isOpen)
        );
    },
    panelOuterClass: "o-discuss-PinnedMessagesPanel bg-inherit",
    icon: "fa fa-fw fa-thumb-tack",
    iconLarge: "fa fa-fw fa-lg fa-thumb-tack",
    name: _t("Pinned Messages"),
    nameActive: _t("Hide Pinned Messages"),
    sequence: 20,
    sequenceGroup: 10,
    setup(action) {
        useChildSubEnv({
            pinMenu: {
                open: () => action.open(),
                close: () => {
                    if (action.isActive) {
                        action.close();
                    }
                },
            },
        });
    },
    toggle: true,
});
