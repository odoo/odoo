import { CountryFlag } from "@mail/core/common/country_flag";
import { ImStatus } from "@mail/core/common/im_status";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { discussSidebarItemsRegistry } from "@mail/core/public_web/discuss_sidebar";
import { cleanTerm } from "@mail/utils/common/format";
import { useHover } from "@mail/utils/common/hooks";

import { Component, useState, useSubEnv } from "@odoo/owl";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { markEventHandled } from "@web/core/utils/misc";

export const discussSidebarChannelIndicatorsRegistry = registry.category(
    "mail.discuss_sidebar_channel_indicators"
);

export class DiscussSidebarChannel extends Component {
    static template = "mail.DiscussSidebarChannel";
    static props = ["thread"];
    static components = { CountryFlag, Dropdown, ImStatus, ThreadIcon };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.dialogService = useService("dialog");
        this.hover = useHover(["root", "floating*"], {
            onHover: () => (this.floating.isOpen = true),
            onAway: () => (this.floating.isOpen = false),
        });
        this.floating = useDropdownState();
    }

    get attClass() {
        return {
            "bg-inherit": this.thread.notEq(this.store.discuss.thread),
            "o-active": this.thread.eq(this.store.discuss.thread),
            "o-unread":
                this.thread.selfMember?.message_unread_counter > 0 && !this.thread.isMuted,
            "opacity-50": this.thread.mute_until_dt,
            "position-relative justify-content-center mx-2 o-compact":
                this.store.discuss.isSidebarCompact,
            "mx-2": !this.store.discuss.isSidebarCompact,
        };
    }

    get indicators() {
        return discussSidebarChannelIndicatorsRegistry.getAll();
    }

    get commands() {
        const commands = [];
        if (this.thread.canLeave) {
            commands.push({
                onSelect: () => this.leaveChannel(),
                label: _t("Leave Channel"),
                icon: "oi oi-close",
                sequence: 20,
            });
        }
        if (this.thread.canUnpin) {
            commands.push({
                onSelect: () => this.thread.unpin(),
                label: _t("Unpin Conversation"),
                icon: "oi oi-close",
                sequence: 20,
            });
        }
        return commands;
    }

    get sortedCommands() {
        const commands = [...this.commands];
        commands.sort((c1, c2) => c1.sequence - c2.sequence);
        return commands;
    }

    /** @returns {import("models").Thread} */
    get thread() {
        return this.props.thread;
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

    async leaveChannel() {
        const thread = this.thread;
        if (thread.channel_type !== "group" && thread.create_uid === thread.store.self.userId) {
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

    /** @param {MouseEvent} ev */
    openThread(ev, thread) {
        markEventHandled(ev, "sidebar.openThread");
        thread.setAsDiscussThread();
    }
}

export class DiscussSidebarCategory extends Component {
    static template = "mail.DiscussSidebarCategory";
    static props = ["category"];
    static components = { Dropdown };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.discusscorePublicWebService = useState(useService("discuss.core.public.web"));
        this.hover = useHover(["root", "floating*"], {
            onHover: () => this.onHover(true),
            onAway: () => this.onHover(false),
        });
        this.floating = useDropdownState();
    }

    onHover(hovering) {
        this.floating.isOpen = hovering;
    }

    /** @returns {import("models").DiscussAppCategory} */
    get category() {
        return this.props.category;
    }

    get actions() {
        return [];
    }

    toggle() {
        if (this.store.channels.status === "fetching") {
            return;
        }
        this.category.open = !this.category.open;
        this.discusscorePublicWebService.broadcastCategoryState(this.category);
    }
}

export class DiscussSidebarQuickSearchInput extends Component {
    static template = "mail.DiscussSidebarQuickSearchInput";
    static props = ["state", "autofocus?"];

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        if (this.props.autofocus) {
            useAutofocus({ refName: "root" });
        }
    }

    get state() {
        return this.props.state;
    }
}

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarCategories extends Component {
    static template = "mail.DiscussSidebarCategories";
    static props = {};
    static components = {
        DiscussSidebarCategory,
        DiscussSidebarChannel,
        DiscussSidebarQuickSearchInput,
        Dropdown,
    };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.discusscorePublicWebService = useState(useService("discuss.core.public.web"));
        this.state = useState({ quickSearchVal: "", floatingQuickSearchOpen: false });
        this.orm = useService("orm");
        this.quickSearchHover = useHover(["quick-search-btn", "quick-search-floating*"], {
            onHover: () => (this.quickSearchFloating.isOpen = true),
            onAway: () => {
                if (!this.quickSearchHover.isHover && !this.state.quickSearchVal.length) {
                    this.state.floatingQuickSearchOpen = false;
                }
            },
        });
        this.quickSearchFloating = useDropdownState();
        useSubEnv({
            filteredThreads: (threads) => this.filteredThreads(threads),
        });
    }

    filteredThreads(threads) {
        return threads.filter(
            (thread) =>
                thread.displayInSidebar &&
                (!this.state.quickSearchVal ||
                    cleanTerm(thread.displayName).includes(cleanTerm(this.state.quickSearchVal)))
        );
    }

    get hasQuickSearch() {
        return (
            Object.values(this.store.Thread.records).filter(
                (thread) => thread.is_pinned && thread.model === "discuss.channel"
            ).length > 19
        );
    }
}

discussSidebarItemsRegistry.add("channels", DiscussSidebarCategories, { sequence: 30 });
