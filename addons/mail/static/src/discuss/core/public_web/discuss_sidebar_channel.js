import { CountryFlag } from "@mail/core/common/country_flag";
import { DiscussSidebarChannelActions } from "@mail/discuss/core/public_web/discuss_sidebar_channel_actions";
import { DiscussSidebarSubchannel } from "@mail/discuss/core/public_web/discuss_sidebar_subchannel";
import { ImStatus } from "@mail/core/common/im_status";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { useHover, UseHoverOverlay } from "@mail/utils/common/hooks";

import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { markEventHandled } from "@web/core/utils/misc";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";

export const discussSidebarChannelIndicatorsRegistry = registry.category(
    "mail.discuss_sidebar_channel_indicators"
);

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
        if (this.thread.channel?.channel_type === "channel") {
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
        if (!this.thread.discussAppCategory.is_open) {
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
