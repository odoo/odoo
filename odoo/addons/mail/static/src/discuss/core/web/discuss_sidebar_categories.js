/* @odoo-module */

import { ImStatus } from "@mail/core/common/im_status";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { discussSidebarItemsRegistry } from "@mail/core/web/discuss_sidebar";
import { ChannelSelector } from "@mail/discuss/core/web/channel_selector";
import { onExternalClick } from "@mail/utils/common/hooks";
import { cleanTerm } from "@mail/utils/common/format";

import { Component, useState } from "@odoo/owl";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { markEventHandled } from "@web/core/utils/misc";

export const discussSidebarCategoriesRegistry = registry.category(
    "mail.discuss_sidebar_categories"
);
export const discussSidebarChannelIndicatorsRegistry = registry.category(
    "mail.discuss_sidebar_channel_indicators"
);

discussSidebarCategoriesRegistry.add(
    "channels",
    { value: (store) => store.discuss.channels },
    { sequence: 10 }
);
discussSidebarCategoriesRegistry.add(
    "chats",
    { value: (store) => store.discuss.chats },
    { sequence: 30 }
);

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarCategories extends Component {
    static template = "mail.DiscussSidebarCategories";
    static props = {};
    static components = { ChannelSelector, ImStatus, ThreadIcon };

    setup() {
        this.store = useState(useService("mail.store"));
        this.threadService = useState(useService("mail.thread"));
        this.state = useState({
            editing: false,
            quickSearchVal: "",
        });
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.userSettings = useService("mail.user_settings");
        this.orm = useService("orm");
        onExternalClick("selector", () => {
            this.state.editing = false;
        });
    }

    addToCategory(category) {
        this.state.editing = category.id;
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

    get categories() {
        return discussSidebarCategoriesRegistry.getAll();
    }

    get channelIndicators() {
        return discussSidebarChannelIndicatorsRegistry.getAll();
    }

    filteredThreads(category) {
        return category.threads.filter((thread) => {
            return (
                (thread.displayToSelf || thread.isLocallyPinned) &&
                (!this.state.quickSearchVal ||
                    cleanTerm(thread.displayName).includes(cleanTerm(this.state.quickSearchVal)))
            );
        });
    }

    get hasQuickSearch() {
        return (
            Object.values(this.store.Thread.records).filter(
                (thread) => thread.is_pinned && thread.model === "discuss.channel"
            ).length > 19
        );
    }

    /**
     * @param {import("models").Thread} thread
     */
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

    openCategory(category) {
        if (category.id === "channels") {
            this.actionService.doAction({
                name: _t("Public Channels"),
                type: "ir.actions.act_window",
                res_model: "discuss.channel",
                views: [
                    [false, "kanban"],
                    [false, "form"],
                ],
                domain: [["channel_type", "=", "channel"]],
            });
        }
    }

    /**
     * @param {import("models").Thread} thread
     */
    openSettings(thread) {
        if (thread.type === "channel") {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "discuss.channel",
                res_id: thread.id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("models").Thread} thread
     */
    openThread(ev, thread) {
        markEventHandled(ev, "sidebar.openThread");
        this.threadService.setDiscussThread(thread);
    }

    stopEditing() {
        this.state.editing = false;
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
}

discussSidebarItemsRegistry.add("channels", DiscussSidebarCategories, { sequence: 30 });
