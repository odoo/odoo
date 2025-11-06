import { CountryFlag } from "@mail/core/common/country_flag";
import { DiscussSidebarChannelActions } from "@mail/discuss/core/public_web/discuss_app/sidebar/channel_actions";
import { DiscussSidebarSubchannel } from "@mail/discuss/core/public_web/discuss_app/sidebar/subchannel";
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
    static props = ["channel"];
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
        if (this.channel.channel_type === "channel") {
            return _t("Channel Actions");
        }
        return _t("Chat Actions");
    }

    get attClass() {
        return {
            "bg-inherit": !this.channel.discussAppAsThread,
            "o-active": this.channel.discussAppAsThread,
            "o-unread":
                this.channel.self_member_id?.message_unread_counter > 0 &&
                !this.channel.self_member_id?.mute_until_dt,
            "border-bottom-0 rounded-bottom-0": this.bordered,
            "opacity-50": this.channel.self_member_id?.mute_until_dt,
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
            Boolean(this.channel.subChannelsInSidebar?.length)
        );
    }

    get indicators() {
        return discussSidebarChannelIndicatorsRegistry.getAll();
    }

    get itemNameAttClass() {
        return {
            "o-unread fw-bolder":
                this.channel.self_member_id?.message_unread_counter > 0 &&
                !this.channel.self_member_id?.mute_until_dt,
            "opacity-75 opacity-100-hover":
                this.channel.self_member_id?.message_unread_counter === 0 ||
                this.channel.self_member_id?.mute_until_dt,
        };
    }

    /** @returns {import("models").DiscussChannel} */
    get channel() {
        return this.props.channel;
    }

    get threadAvatarAttClass() {
        return {};
    }

    get subChannels() {
        return this.channel.subChannelsInSidebar;
    }

    showChannel(sub) {
        if (sub.discussAppAsThread) {
            return true;
        }
        if (!this.channel.discussAppCategory.is_open) {
            return false;
        }
        if (
            !this.channel.self_member_id?.mute_until_dt ||
            sub.self_member_id?.message_unread_counter > 0
        ) {
            return true;
        }
        return (
            this.isSelfOrThreadActive &&
            !(this.channel.self_member_id?.mute_until_dt && sub.self_member_id?.mute_until_dt)
        );
    }

    get showThreadIcon() {
        return (
            this.channel.channel_type === "chat" ||
            (this.channel.channel_type === "channel" && !this.channel.group_public_id) ||
            (this.channel.channel_type === "group" && this.channel.hasOtherMembersTyping)
        );
    }

    get isSelfOrThreadActive() {
        return (
            this.channel.discussAppAsThread ||
            this.subChannels.some((sub) => sub.discussAppAsThread)
        );
    }

    /** @param {MouseEvent} ev */
    openChannel(ev, channel) {
        markEventHandled(ev, "sidebar.openChannel");
        channel.open();
    }
}
