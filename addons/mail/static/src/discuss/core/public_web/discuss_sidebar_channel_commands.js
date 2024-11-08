import { useChannelActions } from "@mail/discuss/core/common/channel_actions";

import { Component, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {function} [close]
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarChannelCommands extends Component {
    static template = "mail.DiscussSidebarChannelCommands";
    static components = { ConfirmationDialog };
    static props = ["thread", "close?"];

    setup() {
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.sidebarChannelActions = useChannelActions();
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
