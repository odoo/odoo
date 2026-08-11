import { CountryFlag } from "@mail/core/common/country_flag";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { MessagingMenuItem } from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import { propStatic, usePropsPlus, useLongPress } from "@mail/utils/common/hooks";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";

import { types } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

Object.assign(MessagingMenuItem.components, { CountryFlag });

/** @type {MessagingMenuItem} */
const messagingMenuItemPatch = {
    setup() {
        super.setup(...arguments);
        this.channelDropdownState = useDropdownState();
        // `super.setup()` already assigned `this.props`; merge this patch's own prop into it
        // rather than replacing it, so the base props (message, onClick, activeTab) survive.
        Object.assign(
            this.props,
            usePropsPlus({
                channel: propStatic(types.instanceOf(this.store["discuss.channel"]).optional()),
            })
        );
        this.isDiscussSidebarChannelActions = true;
        this.threadActions = useThreadActions({ thread: () => this.props.channel?.thread });
        if (isMobileOS()) {
            useLongPress(this.root, {
                action: () => {
                    if (this.props.channel) {
                        this.channelDropdownState.open();
                    }
                },
            });
        }
    },
    get _isActive() {
        return (
            this.store.discuss.isActive &&
            Boolean(this.props.channel?.thread?.eq(this.store.discuss.thread))
        );
    },
    get actionsButtonClass() {
        return this.props.channel
            ? { ...super.actionsButtonClass, "me-1": this.props.channel?.parent_channel_id }
            : super.actionsButtonClass;
    },
    get actionsButtonTitle() {
        return this.props.channel ? this.actionsTitle : super.actionsButtonTitle;
    },
    get actionsDropdownState() {
        return this.props.channel ? this.channelDropdownState : super.actionsDropdownState;
    },
    _computeActionsPartition() {
        return this.props.channel ? this.threadActions.partition : super._computeActionsPartition();
    },
    get actionsTitle() {
        return this.props.channel?.isChatChannel
            ? _t("Chat Actions")
            : this.props.channel
            ? _t("Channel Actions")
            : super.actionsTitle;
    },
    get itemName() {
        return this.props.channel?.thread?.displayName ?? super.itemName;
    },
    get itemPreviewThread() {
        return super.itemPreviewThread || this.props.channel?.thread;
    },
    get notificationItemProps() {
        if (!this.props.channel) {
            return super.notificationItemProps;
        }
        const displayedMessage =
            this.props.channel.isChatChannel ||
            (this.props.channel.channel_type === "channel" &&
                this.props.channel.needactionMessages.length === 0)
                ? this.props.channel.newestPersistentOfAllMessage
                : this.props.channel.sortedNeedactionMessages.at(-1);
        const swipeRight = this.props.channel.isUnread
            ? {
                  action: () => this.props.channel.thread.markAsRead(),
                  icon: "check_circle",
                  bgColor: "bg-success",
              }
            : undefined;
        return {
            thread: this.props.channel.thread,
            className: "border-0 rounded-3",
            message: displayedMessage,
            counter: this.props.channel.importantCounter ?? this.props.channel.needactionCounter,
            datetime: displayedMessage?.datetime ?? this.props.channel.create_date,
            iconSrc: this.props.channel.thread.avatarUrl,
            important: !!(
                this.props.channel.importantCounter ?? this.props.channel.needactionCounter
            ),
            isActive: this.isActive(),
            muted: this.props.channel.self_member_id?.mute_until_dt
                ? 2
                : !this.props.channel.isUnread
                ? 1
                : 0,
            textClassName: "text-truncate",
            onSwipeRight: this.hasTouch() ? swipeRight : undefined,
            onSwipeLeft: this.swipeLeft ?? undefined,
            onClick: () => this.props.onClick(this.props.channel),
        };
    },
    get parentChannelShortName() {
        const name = this.props.channel?.parent_channel_id?.displayName ?? "";
        const maxLength = 4;
        return name.length > maxLength ? `${name.slice(0, maxLength)}…` : name;
    },
    get prependNameWithStar() {
        return this.props.channel?.self_member_id?.is_favorite;
    },
    get showActions() {
        return super.showActions || Boolean(this.props.channel);
    },
    get starTitle() {
        return _t("Favorite");
    },
    get swipeLeft() {
        if (this.hasTouch() && this.props.channel?.canHide) {
            return {
                action: () => this.props.channel.unpinChannel(),
                icon: "cancel",
                bgColor: "bg-danger",
            };
        }
        return super.swipeLeft;
    },
};
patch(MessagingMenuItem.prototype, messagingMenuItemPatch);
