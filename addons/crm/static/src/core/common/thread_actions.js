import { registerThreadAction } from "@mail/core/common/thread_actions";
import { ChannelCommandDialog } from "@mail/discuss/core/common/channel_command_dialog";

import { _t } from "@web/core/l10n/translation";

registerThreadAction("create-lead", {
    condition: ({ channel, owner }) =>
        channel?.allowCreateLead && !owner.isDiscussSidebarChannelActions,
    icon: "handshake",
    name: _t("Create Lead"),
    panel: {
        component: ChannelCommandDialog,
        props: ({ channel }) => ({
            channel,
            commandName: "lead",
            icon: "handshake",
            placeholderText: _t("e.g. Product pricing"),
            title: _t("Create Lead"),
        }),
    },
    sequence: 10,
    sequenceGroup: 25,
});
