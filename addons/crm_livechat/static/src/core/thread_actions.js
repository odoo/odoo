import { LivechatCommandDialog } from "@im_livechat/core/common/livechat_command_dialog";

import { registerThreadAction } from "@mail/core/common/thread_actions";
import "@mail/discuss/call/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

registerThreadAction("create-lead", {
    actionPanelComponent: LivechatCommandDialog,
    actionPanelComponentProps: ({ action }) => ({
        close: () => action.close(),
        commandName: "lead",
        placeholderText: _t("e.g. Product pricing"),
        title: _t("Create Lead"),
        icon: "fa fa-handshake-o",
    }),
    close: ({ action }) => action.popover?.close(),
    condition: false, // managed by ThreadAction patch
    panelOuterClass: "bg-100",
    icon: "fa fa-handshake-o",
    name: _t("Create Lead"),
    sequence: 10,
    sequenceGroup: 25,
    setup({ owner }) {
        if (!owner.env.inChatWindow) {
            this.popover = usePopover(LivechatCommandDialog, {
                onClose: () => this.close(),
                popoverClass: this.panelOuterClass,
            });
        }
    },
    toggle: true,
    open({ owner, thread }) {
        this.popover?.open(owner.root.el.querySelector(`[name="${this.id}"]`), {
            thread,
            ...this.actionPanelComponentProps,
        });
    },
});
