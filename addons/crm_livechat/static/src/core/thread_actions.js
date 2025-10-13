import { LivechatCommandDialog } from "@im_livechat/core/common/livechat_command_dialog";

import { registerThreadAction } from "@mail/core/common/thread_actions";
import "@mail/discuss/call/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

registerThreadAction("create-lead", {
    actionPanelClose: ({ action }) => action.popover?.close(),
    actionPanelComponent: LivechatCommandDialog,
    actionPanelComponentProps: ({ action }) => ({
        close: () => action.actionPanelClose(),
        commandName: "lead",
        placeholderText: _t("e.g. Product pricing"),
        title: _t("Create Lead"),
        icon: "fa fa-handshake-o",
    }),
    actionPanelOpen({ owner, thread }) {
        this.popover?.open(owner.root.el.querySelector(`[name="${this.id}"]`), {
            thread,
            ...this.actionPanelComponentProps,
        });
    },
    actionPanelOuterClass: "bg-100",
    condition: false, // managed by ThreadAction patch
    icon: "fa fa-handshake-o",
    name: _t("Create Lead"),
    sequence: 10,
    sequenceGroup: 25,
    setup({ owner }) {
        if (!owner.env.inChatWindow) {
            this.popover = usePopover(LivechatCommandDialog, {
                onClose: () => this.actionPanelClose(),
                popoverClass: this.actionPanelOuterClass,
            });
        }
    },
});
