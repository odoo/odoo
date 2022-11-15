/** @odoo-module */

import { useMessaging } from "../messaging_hook";
import { ThreadIcon } from "./thread_icon";
import { ChannelSelector } from "./channel_selector";
import { PartnerImStatus } from "./partner_im_status";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { onExternalClick } from "../utils";
import { Component, useState } from "@odoo/owl";

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
