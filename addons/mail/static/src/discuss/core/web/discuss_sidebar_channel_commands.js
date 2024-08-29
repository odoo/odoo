import { Component, useState, useRef } from "@odoo/owl";
import { useSidebarActions } from "../common/channel_actions";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class DiscussSidebarChannelCommands extends Component {
    static template = "mail.DiscussSidebar.channelCommands";
    static props = {
        thread: { optional: true, type: Object },
        close: { optional: true, type: Function },
    };
    static components = { ConfirmationDialog };

    setup() {
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.root = useRef("root");
        this.sidebarChannelActions = useSidebarActions();
        this.store = useState(useService("mail.store"));
    }

    askConfirmation(body) {
        return new Promise((resolve) => {
            this.dialogService.add(ConfirmationDialog, {
                body: body,
                confirmLabel: _t("Leave Conversation"),
                confirm: resolve,
                cancel: () => {},
            });
        });
    }

    /**
     * @param {import("models").Thread} thread
     */
    async leaveChannel(thread) {
        if (thread.channel_type !== "group" && thread.create_uid === thread.store.self.userId) {
            await this.askConfirmation(
                _t("You are the admistrator of this channel. Are you sure you want to leave?")
            );
        }
        if (thread.channel_type === "group") {
            await this.askConfirmation(
                _t(
                    "You are about to leave this group conversation and will no longer have access to it unless you are invited again. Are you sure you want to continue?"
                )
            );
        }
        thread.leave();
    }

    /**
     * @param {import("models").Thread} thread
     */
    channelInfo(thread) {
        if (thread) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "discuss.channel",
                views: [[false, "form"]],
                res_id: thread.id,
                target: "current",
            });
        }
    }
}
