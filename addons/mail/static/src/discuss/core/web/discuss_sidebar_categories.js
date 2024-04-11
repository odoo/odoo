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

export const discussSidebarChannelIndicatorsRegistry = registry.category(
    "mail.discuss_sidebar_channel_indicators"
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
        super.setup();
        this.store = useState(useService("mail.store"));
        this.discussCoreWebService = useState(useService("discuss.core.web"));
        this.state = useState({
            editing: false,
            quickSearchVal: "",
        });
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
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
        if (thread.channel_type !== "group" && thread.isAdmin) {
            await this.askConfirmation(
                _t("You are the administrator of this channel. Are you sure you want to leave?")
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
        if (thread.channel_type === "channel") {
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
        thread.setAsDiscussThread();
    }

    stopEditing() {
        this.state.editing = false;
    }

    /**
     *
     * @param {import("models").DiscussAppCategory} category
     */
    toggleCategory(category) {
        category.open = !category.open;
        this.discussCoreWebService.broadcastCategoryState(category);
    }
}

discussSidebarItemsRegistry.add("channels", DiscussSidebarCategories, { sequence: 30 });
