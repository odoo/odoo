/* @odoo-module */

import { useMessaging, useStore } from "@mail/new/core/messaging_hook";
import { ThreadIcon } from "@mail/new/discuss/thread_icon";
import { ChannelSelector } from "@mail/new/discuss/channel_selector";
import { PartnerImStatus } from "@mail/new/discuss/partner_im_status";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { onExternalClick } from "@mail/new/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { markEventHandled } from "@mail/new/utils/misc";
import { ChatWindowIcon } from "@mail/new/web/chat_window/chat_window_icon";

import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class Sidebar extends Component {
    static template = "mail.discuss_sidebar";
    static components = { ChannelSelector, ThreadIcon, PartnerImStatus, ChatWindowIcon };
    static props = [];

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        /** @type {import("@mail/new/core/thread_service").ThreadService} */
        this.threadService = useState(useService("mail.thread"));
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.userSettings = useService("mail.user_settings");
        this.orm = useService("orm");
        this.state = useState({
            editing: false,
            quickSearchVal: "",
        });
        onExternalClick("selector", () => {
            this.state.editing = false;
        });
    }

    openThread(ev, thread) {
        markEventHandled(ev, "sidebar.openThread");
        this.threadService.setDiscussThread(thread);
    }

    async toggleCategory(category) {
        category.isOpen = !category.isOpen;
        await this.orm.call(
            "res.users.settings",
            "set_res_users_settings",
            [[this.userSettings.id]],
            {
                new_settings: {
                    [category.serverStateKey]: category.isOpen,
                },
            }
        );
    }

    openCategory(category) {
        if (category.id === "channels") {
            this.actionService.doAction({
                name: _t("Public Channels"),
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
                _t("You are the administrator of this channel. Are you sure you want to leave?")
            );
        }
        if (thread.type === "group") {
            await this.askConfirmation(
                _t(
                    "You are about to leave this group conversation and will no longer have access to it unless you are invited again. Are you sure you want to continue?"
                )
            );
        }
        this.threadService.leaveChannel(thread);
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

    get hasQuickSearch() {
        return (
            Object.values(this.store.threads).filter(
                (thread) => thread.is_pinned && thread.model === "mail.channel"
            ).length > 19
        );
    }

    filteredThreads(category) {
        if (!this.state.quickSearchVal) {
            return category.threads;
        }
        return category.threads.filter((threadLocalId) => {
            const thread = this.store.threads[threadLocalId];
            return thread.name.includes(this.state.quickSearchVal);
        });
    }
}
