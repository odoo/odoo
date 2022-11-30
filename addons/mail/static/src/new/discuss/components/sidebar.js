/** @odoo-module **/

import { ChannelSelector } from "@mail/new/discuss/components/channel_selector";
import { PartnerImStatus } from "@mail/new/discuss/components/partner_im_status";
import { ThreadIcon } from "@mail/new/discuss/components/thread_icon";
import { useMessaging } from "@mail/new/messaging_hook";
import { onExternalClick } from "@mail/new/utils";

import { Component, useState } from "@odoo/owl";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";

export class Sidebar extends Component {
    setup() {
        this.messaging = useMessaging();
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.state = useState({
            editing: false,
        });
        onExternalClick("selector", () => {
            this.state.editing = false;
        });
    }

    openThread(id) {
        this.messaging.setDiscussThread(id);
    }

    toggleCategory(category) {
        category.isOpen = !category.isOpen;
    }

    openCategory(category) {
        if (category.id === "channels") {
            this.actionService.doAction({
                name: this.env._t("Public Channels"),
                type: "ir.actions.act_window",
                res_model: "mail.channel",
                views: [
                    [false, "kanban"],
                    [false, "form"],
                ],
                domain: [["channel_type", "=", "channel"]],
            });
        }
    }

    openSettings(thread) {
        if (thread.type === "channel") {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "mail.channel",
                res_id: thread.id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    addToCategory(category) {
        this.state.editing = category.id;
    }

    stopEditing() {
        this.state.editing = false;
    }

    async leaveChannel(thread) {
        if (thread.type !== "group" && thread.isAdmin) {
            await this.askConfirmation(
                this.env._t(
                    "You are the administrator of this channel. Are you sure you want to leave?"
                )
            );
        }
        if (thread.type === "group") {
            await this.askConfirmation(
                this.env._t(
                    "You are about to leave this group conversation and will no longer have access to it unless you are invited again. Are you sure you want to continue?"
                )
            );
        }
        this.messaging.leaveChannel(thread.id);
    }

    askConfirmation(body) {
        return new Promise((resolve) => {
            this.dialogService.add(ConfirmationDialog, {
                body: body,
                confirm: resolve,
                cancel: () => {},
            });
        });
    }
}

Object.assign(Sidebar, {
    components: { ChannelSelector, ThreadIcon, PartnerImStatus },
    props: [],
    template: "mail.discuss_sidebar",
});
