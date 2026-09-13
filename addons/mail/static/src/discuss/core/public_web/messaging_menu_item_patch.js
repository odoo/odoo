import { CountryFlag } from "@mail/core/common/country_flag";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { MessagingMenuItem } from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import { useLongPress } from "@mail/utils/common/hooks";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

import { types, useProps } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

Object.assign(MessagingMenuItem.components, { CountryFlag });

/** @type {MessagingMenuItem} */
const messagingMenuItemPatch = {
    setup() {
        super.setup(...arguments);
        this.channelDropdownState = useDropdownState();
        this.channel = useProps.static(
            "channel",
            types.instanceOf(this.store["discuss.channel"]).optional()
        );
        this.isDiscussSidebarChannelActions = true;
        this.threadActions = useThreadActions({ thread: () => this.channel?.thread });
        if (isMobileOS()) {
            useLongPress(this.root, {
                action: () => {
                    if (this.channel) {
                        this.channelDropdownState.open();
                    }
                },
            });
        }
    },
    get _isActive() {
        return (
            this.store.discuss.isActive &&
            Boolean(this.channel?.thread?.eq(this.store.discuss.thread))
        );
    },
    get actionsButtonClass() {
        return this.channel
            ? { ...super.actionsButtonClass, "me-1": this.channel?.parent_channel_id }
            : super.actionsButtonClass;
    },
    get actionsButtonTitle() {
        return this.channel ? this.actionsTitle : super.actionsButtonTitle;
    },
    get actionsDropdownState() {
        return this.channel ? this.channelDropdownState : super.actionsDropdownState;
    },
    hasActions() {
        return this.channel ? this.threadActions.actionsComputed().length : super.hasActions();
    },
    _computeActionsPartition() {
        return this.channel ? this.threadActions.partition : super._computeActionsPartition();
    },
    get actionsTitle() {
        return this.channel?.isChatChannel
            ? _t("Chat Actions")
            : this.channel
            ? _t("Channel Actions")
            : super.actionsTitle;
    },
    get itemName() {
        return this.channel?.thread?.displayName ?? super.itemName;
    },
    get itemPreviewThread() {
        return super.itemPreviewThread || this.channel?.thread;
    },
    /** The time the meeting of the channel starts at, shown next to its name. */
    get meetingStartText() {
        return this.channel?.meeting_start_dt?.toLocaleString(DateTime.TIME_SIMPLE, {
            locale: user.lang,
        });
    },
    get notificationItemProps() {
        if (!this.channel) {
            return super.notificationItemProps;
        }
        const displayedMessage =
            this.channel.isChatChannel ||
            (this.channel.channel_type === "channel" &&
                this.channel.needactionMessages.length === 0)
                ? this.channel.newestPersistentOfAllMessage
                : this.channel.sortedNeedactionMessages.at(-1);
        const swipeRight = this.channel.isUnread
            ? {
                  action: () => this.channel.thread.markAsRead(),
                  icon: "check_circle",
                  bgColor: "bg-success",
              }
            : undefined;
        return {
            thread: this.channel.thread,
            message: displayedMessage,
            counter: this.channel.importantCounter ?? this.channel.needactionCounter,
            datetime: displayedMessage?.datetime ?? this.channel.create_date,
            iconSrc: this.channel.thread.avatarUrl,
            important: !!(this.channel.importantCounter ?? this.channel.needactionCounter),
            isActive: this.isActive(),
            muted: this.channel.self_member_id?.mute_until_dt ? 2 : !this.channel.isUnread ? 1 : 0,
            textClassName: "text-truncate",
            onSwipeRight: this.hasTouch() ? swipeRight : undefined,
            onSwipeLeft: this.swipeLeft ?? undefined,
            onClick: () => this.onClick(this.channel),
        };
    },
    get parentChannelShortName() {
        const name = this.channel?.parent_channel_id?.displayName ?? "";
        const maxLength = 4;
        return name.length > maxLength ? `${name.slice(0, maxLength)}…` : name;
    },
    get prependNameWithStar() {
        return this.channel?.self_member_id?.is_favorite;
    },
    get showActions() {
        return super.showActions || Boolean(this.channel);
    },
    get starTitle() {
        return _t("Favorite");
    },
    get swipeLeft() {
        if (this.hasTouch() && this.channel?.canHide) {
            return {
                action: () => this.channel.unpinChannel(),
                icon: "cancel",
                bgColor: "bg-danger",
            };
        }
        return super.swipeLeft;
    },
};
patch(MessagingMenuItem.prototype, messagingMenuItemPatch);
