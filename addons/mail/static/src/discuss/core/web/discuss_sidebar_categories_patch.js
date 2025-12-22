import { ChannelSelector } from "@mail/discuss/core/web/channel_selector";
import { onExternalClick } from "@mail/utils/common/hooks";

import { patch } from "@web/core/utils/patch";
import {
    DiscussSidebarCategory,
    DiscussSidebarChannel,
} from "../public_web/discuss_sidebar_categories";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useEffect, useState } from "@odoo/owl";

DiscussSidebarCategory.components = { ...DiscussSidebarCategory.components, ChannelSelector };

/** @type {import("@mail/discuss/core/public_web/discuss_sidebar_categories").DiscussSidebarChannel} */
const DiscussSidebarChannelPatch = {
    setup() {
        super.setup();
        this.actionService = useService("action");
    },
    get commands() {
        const commands = super.commands;
        if (this.thread.channel_type === "channel") {
            commands.push({
                onSelect: () => this.openSettings(),
                label: _t("Channel settings"),
                icon: "fa fa-cog",
                sequence: 10,
            });
        }
        return commands;
    },
    openSettings() {
        if (this.thread.channel_type === "channel") {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "discuss.channel",
                res_id: this.thread.id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    },
};

/** @type {import("@mail/discuss/core/public_web/discuss_sidebar_categories").DiscussSidebarCategory} */
const DiscussSidebarCategoryPatch = {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.state ??= useState({});
        this.state.editing = false;
        onExternalClick("selector", () => (this.state.editing = false));
        useEffect(
            () => {
                if (this.store.discuss.isSidebarCompact && !this.floating.isOpen) {
                    this.state.editing = false;
                }
            },
            () => [this.floating.isOpen]
        );
    },
    addToCategory() {
        this.state.editing = true;
    },
    open() {
        if (this.category.id === "channels") {
            this.actionService.doAction({
                name: _t("Public Channels"),
                type: "ir.actions.act_window",
                res_model: "discuss.channel",
                views: [
                    [false, "kanban"],
                    [false, "form"],
                ],
                domain: [
                    ["channel_type", "=", "channel"],
                    ["parent_channel_id", "=", false],
                ],
            });
        }
    },
    onHover() {
        if (this.state.editing && this.store.discuss.isSidebarCompact) {
            return;
        }
        super.onHover(...arguments);
        if (this.store.discuss.isSidebarCompact && !this.floating.isOpen) {
            this.state.editing = false;
        }
    },
    stopEditing() {
        this.state.editing = false;
    },
    get actions() {
        const actions = super.actions;
        if (this.category.canView) {
            actions.push({
                onSelect: () => this.open(),
                label: _t("View or join channels"),
                icon: "fa fa-cog",
            });
        }
        if (this.category.canAdd && this.category.open) {
            actions.push({
                onSelect: () => this.addToCategory(),
                label: this.category.addTitle,
                icon: "fa fa-plus",
                hotkey: this.category.addHotkey,
                class: "o-mail-DiscussSidebarCategory-add",
            });
        }
        return actions;
    },
};

patch(DiscussSidebarChannel.prototype, DiscussSidebarChannelPatch);
patch(DiscussSidebarCategory.prototype, DiscussSidebarCategoryPatch);
