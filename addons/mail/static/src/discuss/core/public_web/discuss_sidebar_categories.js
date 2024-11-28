import { CountryFlag } from "@mail/core/common/country_flag";
import { ImStatus } from "@mail/core/common/im_status";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { discussSidebarItemsRegistry } from "@mail/core/public_web/discuss_sidebar";
import { useHover, useLoadMore } from "@mail/utils/common/hooks";

import { Component, onMounted, useState, useSubEnv } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { markEventHandled } from "@web/core/utils/misc";

export const discussSidebarChannelIndicatorsRegistry = registry.category(
    "mail.discuss_sidebar_channel_indicators"
);

export class DiscussSidebarSubchannel extends Component {
    static template = "mail.DiscussSidebarSubchannel";
    static props = ["thread", "isFirst?"];
    static components = { Dropdown };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.hover = useHover(["root", "floating*"], {
            onHover: () => (this.floating.isOpen = true),
            onAway: () => (this.floating.isOpen = false),
        });
        this.floating = useDropdownState();
    }

    get thread() {
        return this.props.thread;
    }

    get commands() {
        const commands = [];
        if (this.thread.canUnpin) {
            commands.push({
                onSelect: () => this.thread.unpin(),
                label: _t("Unpin Thread"),
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

    /** @param {MouseEvent} ev */
    openThread(ev, thread) {
        markEventHandled(ev, "sidebar.openThread");
        thread.setAsDiscussThread();
    }
}

export class DiscussSidebarChannel extends Component {
    static template = "mail.DiscussSidebarChannel";
    static props = ["thread"];
    static components = { CountryFlag, DiscussSidebarSubchannel, Dropdown, ImStatus, ThreadIcon };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
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
            "o-unread": this.thread.selfMember?.message_unread_counter > 0 && !this.thread.isMuted,
            "border-bottom-0 rounded-bottom-0": this.bordered,
            "opacity-50": this.thread.isMuted,
            "position-relative justify-content-center o-compact mt-0 p-1":
                this.store.discuss.isSidebarCompact,
            "px-0": !this.store.discuss.isSidebarCompact,
        };
    }

    get attClassContainer() {
        return {
            "border border-dark rounded-2 o-bordered": this.bordered,
            "o-compact": this.store.discuss.isSidebarCompact,
        };
    }

    get bordered() {
        return (
            this.store.discuss.isSidebarCompact &&
            Boolean(this.env.filteredThreads?.(this.thread.sub_channel_ids)?.length)
        );
    }

    get indicators() {
        return discussSidebarChannelIndicatorsRegistry.getAll();
    }

    get commands() {
        const commands = [];
        if (this.thread.canLeave) {
            commands.push({
                onSelect: () => this.thread.leaveChannel(),
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

    /** @param {MouseEvent} ev */
    openThread(ev, thread) {
        markEventHandled(ev, "sidebar.openThread");
        thread.setAsDiscussThread();
    }
}

export class DiscussSidebarCategoryHeader extends Component {
    static template = "mail.DiscussSidebarCategoryHeader";
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
        this.category.open = !this.category.open;
        this.discusscorePublicWebService.broadcastCategoryState(this.category);
    }
}

export class DiscussSidebarCategory extends Component {
    static template = "mail.DiscussSidebarCategory";
    static props = ["category"];
    static components = { DiscussSidebarCategoryHeader, DiscussSidebarChannel, Dropdown };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.state = useState({ allLoaded: false });
        this.lastLoad = { offset: undefined, from_important: undefined, all_loaded: false };
        this.loadMore = useLoadMore("load-more", {
            fn: () => this.load(),
            ready: false,
        });
        onMounted(() => this.load().then(() => (this.loadMore.ready = true)));
    }

    get channel_types() {
        switch (this.props.category.id) {
            case "channels":
                return ["channel"];
            case "chats":
                return ["group", "chat"];
            case "whatsapp":
                return ["whatsapp"];
            default:
                return ["livechat"];
        }
    }

    async load() {
        const { storeData, ...otherData } = await rpc("/discuss/pinned_channels/load", {
            offset: this.lastLoad.offset,
            from_important: this.lastLoad.from_important,
            channel_types: this.channel_types,
            by_name: true,
        });
        this.lastLoad = { ...otherData };
        if (this.lastLoad.all_loaded) {
            this.state.allLoaded = true;
        }
        this.store.insert(storeData, { html: true });
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
        Dropdown,
    };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.discusscorePublicWebService = useState(useService("discuss.core.public.web"));
        this.orm = useService("orm");
        this.ui = useState(useService("ui"));
        this.command = useService("command");
        this.searchHover = useHover(["search-btn", "search-floating*"], {
            onHover: () => (this.searchFloating.isOpen = true),
            onAway: () => (this.searchFloating.isOpen = false),
        });
        this.searchFloating = useDropdownState();
        useSubEnv({
            filteredThreads: (threads) => this.filteredThreads(threads),
        });
    }

    filteredThreads(threads) {
        return threads.filter((thread) => thread.displayInSidebar);
    }

    onClickFindOrStartConversation() {
        this.command.openMainPalette({ searchValue: "@" });
    }
}

discussSidebarItemsRegistry.add("channels", DiscussSidebarCategories, { sequence: 30 });
