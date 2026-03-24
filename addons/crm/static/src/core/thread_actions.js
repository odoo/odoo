import { registerThreadAction } from "@mail/core/common/thread_actions";
import { ChannelCommandDialog } from "@mail/discuss/core/common/channel_command_dialog";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

registerThreadAction("create-lead", {
    actionPanelComponent: ChannelCommandDialog,
    actionPanelComponentProps: ({ channel }) => ({
        commandName: "lead",
        placeholderText: _t("e.g. Product pricing"),
        channel,
        title: _t("Create Lead"),
        icon: "fa fa-handshake-o",
    }),
    actionPanelOpen({ rootRef }) {
        this.popover?.open(
            rootRef().querySelector(`[name="${this.id}"]`),
            this.actionPanelComponentProps
        );
    },
    actionPanelOuterClass: "bg-100",
    condition: ({ channel, owner }) => channel?.allowCreateLead && !owner.isDiscussSidebarChannelActions,
    icon: "fa fa-handshake-o",
    name: _t("Create Lead"),
    sequence: 10,
    sequenceGroup: 25,
    setup({ owner }) {
        if (!owner.env.inChatWindow) {
            this.popover = usePopover(ChannelCommandDialog, {
                onClose: () => this.actionPanelClose(),
                popoverClass: this.actionPanelOuterClass,
            });
        }
    },
});
