import { CountryFlag } from "@mail/core/common/country_flag";
import { ImStatus } from "@mail/core/common/im_status";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { discussSidebarItemsRegistry } from "@mail/core/public_web/discuss_sidebar";
import { DiscussSidebarChannelActions } from "@mail/discuss/core/public_web/discuss_sidebar_channel_actions";
import { useHover, UseHoverOverlay } from "@mail/utils/common/hooks";

import { Component, useSubEnv } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { markEventHandled } from "@web/core/utils/misc";

export const discussSidebarChannelIndicatorsRegistry = registry.category(
    "mail.discuss_sidebar_channel_indicators"
);

export class DiscussSidebarSubchannel extends Component {
    static template = "mail.DiscussSidebarSubchannel";
    static props = ["thread", "isFirst?"];
    static components = { DiscussSidebarChannelActions, Dropdown, UseHoverOverlay };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.hover = useHover(["root"], {
            onHover: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.floating.isOpen = true;
                }
            },
            onAway: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.floating.isOpen = false;
                }
            },
            stateObserver: () => [this.floating?.isOpen],
        });
        this.floating = useDropdownState();
        this.showingActions = useDropdownState();
    }

    get actionsTitle() {
        return _t("Thread Actions");
    }

    get thread() {
        return this.props.thread;
    }

    /** @param {MouseEvent} ev */
    openThread(ev, thread) {
        markEventHandled(ev, "sidebar.openThread");
        thread.open();
    }
}

export class DiscussSidebarChannel extends Component {
    static template = "mail.DiscussSidebarChannel";
    static props = ["thread"];
    static components = {
        CountryFlag,
        DiscussSidebarChannelActions,
        DiscussSidebarSubchannel,
        Dropdown,
        ImStatus,
        ThreadIcon,
        UseHoverOverlay,
    };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.hover = useHover(["root"], {
            onHover: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.floating.isOpen = true;
                }
            },
            onAway: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.floating.isOpen = false;
                }
            },
            stateObserver: () => [this.floating?.isOpen],
        });
        this.floating = useDropdownState();
        this.showingActions = useDropdownState();
    }

    get actionsTitle() {
        if (this.thread.channel_type === "channel") {
            return _t("Channel Actions");
        }
        return _t("Chat Actions");
    }

    get attClass() {
        return {
            "bg-inherit": this.thread.notEq(this.store.discuss.thread),
            "o-active": this.thread.eq(this.store.discuss.thread),
            "o-unread":
                this.thread.self_member_id?.message_unread_counter > 0 &&
                !this.thread.self_member_id?.mute_until_dt,
            "border-bottom-0 rounded-bottom-0": this.bordered,
            "opacity-50": this.thread.self_member_id?.mute_until_dt,
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

    get itemNameAttClass() {
        return {
            "o-unread fw-bolder":
                this.thread.self_member_id?.message_unread_counter > 0 &&
                !this.thread.self_member_id?.mute_until_dt,
            "opacity-75 opacity-100-hover":
                this.thread.self_member_id?.message_unread_counter === 0 ||
                this.thread.self_member_id?.mute_until_dt,
        };
    }

    /** @returns {import("models").Thread} */
    get thread() {
        return this.props.thread;
    }

    get threadAvatarAttClass() {
        return {};
    }

    get subChannels() {
        return this.env.filteredThreads?.(this.thread.sub_channel_ids) ?? [];
    }

    showThread(sub) {
        if (sub.eq(this.store.discuss.thread)) {
            return true;
        }
        if (!this.thread.discussAppCategory.open) {
            return false;
        }
        if (
            !this.thread.self_member_id?.mute_until_dt ||
            sub.self_member_id?.message_unread_counter > 0
        ) {
            return true;
        }
        return (
            this.isSelfOrThreadActive &&
            !(this.thread.self_member_id?.mute_until_dt && sub.self_member_id?.mute_until_dt)
        );
    }

    get isSelfOrThreadActive() {
        return (
            this.thread.eq(this.store.discuss.thread) ||
            this.store.discuss.thread?.in(this.subChannels)
        );
    }

    /** @param {MouseEvent} ev */
    openThread(ev, thread) {
        markEventHandled(ev, "sidebar.openThread");
        thread.open();
    }
}

export class DiscussSidebarCategory extends Component {
    static template = "mail.DiscussSidebarCategory";
    static props = ["category"];
    static components = { Dropdown };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.discusscorePublicWebService = useService("discuss.core.public.web");
        this.hover = useHover(["root", "floating"], {
            onHover: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.onHover(true);
                }
            },
            onAway: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.onHover(false);
                }
            },
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
        Dropdown,
    };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.discusscorePublicWebService = useService("discuss.core.public.web");
        this.orm = useService("orm");
        useSubEnv({
            filteredThreads: (threads) => this.filteredThreads(threads),
        });
    }

    filteredThreads(threads) {
        return threads.filter((thread) => thread.displayInSidebar);
    }
}

discussSidebarItemsRegistry.add("channels", DiscussSidebarCategories, { sequence: 30 });
