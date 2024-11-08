import { patch } from "@web/core/utils/patch";
import {
    DiscussSidebarCategory,
    DiscussSidebarChannel,
    DiscussSidebarSubchannel,
} from "../public_web/discuss_sidebar_categories";
import { DiscussSidebarChannelCommands } from "../public_web/discuss_sidebar_channel_commands";
import { usePopover } from "@web/core/popover/popover_hook";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useState, useExternalListener } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

/** @type {import("@mail/discuss/core/public_web/discuss_sidebar_categories").DiscussSidebarChannel} */
const DiscussSidebarChannelPatch = {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.popover = usePopover(DiscussSidebarChannelCommands, {
            position: "right-start",
            onClose: () => {
                this.floating.close();
            },
            popoverClass: "o-mail-DiscussSidebarChannelCommands",
        });
        this.state = useState({
            action: null,
        });
        useExternalListener(
            browser,
            "click",
            () => {
                if (!this.state.action) {
                    this.popover.close();
                }
            },
            { capture: true }
        );
    },
    get commandsMenuBtn() {
        return {
            onSelect: () => {
                this.popover.open(this.root.el, {
                    thread: this.thread,
                    activeAction: (action) => {
                        this.state.action = action;
                    },
                });
            },
            label:
                this.thread.channel_type != "channel"
                    ? _t("Chat Settings")
                    : _t("Channel Settings"),
            icon: this.store.discuss.isSidebarCompact ? "fa fa-cog" : "fa fa-ellipsis-h",
            sequence: 10,
        };
    },
};

/** @type {import("@mail/discuss/core/public_web/discuss_sidebar_categories").DiscussSidebarSubchannel} */
const DiscussSidebarSubchannelPatch = {
    setup() {
        super.setup();
        this.popover = usePopover(DiscussSidebarChannelCommands, {
            position: "right-start",
            onClose: () => this.floating.close(),
            popoverClass: "o-mail-DiscussSidebarChannelCommands",
        });
        this.state = useState({
            action: null,
        });
        useExternalListener(
            browser,
            "click",
            () => {
                if (!this.state.action) {
                    this.popover.close();
                }
            },
            { capture: true }
        );
    },
    get commandsMenuBtn() {
        return {
            onSelect: () => {
                this.popover.open(this.root.el, {
                    thread: this.thread,
                    activeAction: (action) => {
                        this.state.action = action;
                    },
                });
            },
            label: _t("Thread Settings"),
            icon: this.store.discuss.isSidebarCompact ? "fa fa-cog" : "fa fa-ellipsis-h",
        };
    },
};

/** @type {import("@mail/discuss/core/public_web/discuss_sidebar_categories").DiscussSidebarCategory} */
const DiscussSidebarCategoryPatch = {
    setup() {
        super.setup();
        this.actionService = useService("action");
    },
    open() {
        if (this.category.id === "channels") {
            this.actionService.doAction({
                name: _t("Public Channels"),
                type: "ir.actions.act_window",
                res_model: "discuss.channel",
                views: [
                    [false, "kanban"],
                    [false, "list"],
                    [false, "form"],
                ],
                domain: [
                    ["channel_type", "=", "channel"],
                    ["parent_channel_id", "=", false],
                ],
            });
        }
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
        return actions;
    },
};

patch(DiscussSidebarChannel.prototype, DiscussSidebarChannelPatch);
patch(DiscussSidebarCategory.prototype, DiscussSidebarCategoryPatch);
patch(DiscussSidebarSubchannel.prototype, DiscussSidebarSubchannelPatch);
