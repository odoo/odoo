import { CountryFlag } from "@mail/core/common/country_flag";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { MessagingMenuItem } from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import { propComputed, useLongPress } from "@mail/utils/common/hooks";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";

import { types } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

Object.assign(MessagingMenuItem.components, { CountryFlag });

patch(MessagingMenuItem.prototype, {
    setup() {
        super.setup(...arguments);
        this.channelDropdownState = useDropdownState();
        this.channel = propComputed(
            "channel",
            types.instanceOf(this.store["discuss.channel"].Class).optional()
        );
        this.isDiscussSidebarChannelActions = true;
        this.threadActions = useThreadActions({ thread: () => this.channel()?.thread });
        if (isMobileOS()) {
            useLongPress(this.root, {
                action: () => {
                    if (this.channel()) {
                        this.channelDropdownState.open();
                    }
                },
            });
        }
    },
    get _isActive() {
        return (
            this.env.inDiscussApp && Boolean(this.channel()?.thread?.eq(this.store.discuss.thread))
        );
    },
    get actionsTitle() {
        return this.channel()?.isChatChannel
            ? _t("Chat Actions")
            : this.channel()
            ? _t("Channel Actions")
            : super.actionsTitle;
    },
    get itemName() {
        return this.channel()?.thread?.displayName ?? super.itemName;
    },
    get itemPreviewThread() {
        return super.itemPreviewThread || this.channel()?.thread;
    },
    get notificationItemProps() {
        if (!this.channel()) {
            return super.notificationItemProps;
        }
        const displayedMessage =
            this.channel().isChatChannel ||
            (this.channel().channel_type === "channel" &&
                this.channel().needactionMessages.length === 0)
                ? this.channel().newestPersistentOfAllMessage
                : this.channel().needactionMessages.at(-1);
        const swipeRight = this.channel().isUnread
            ? {
                  action: () => this.channel().thread.markAsRead(),
                  icon: "fa-check-circle",
                  bgColor: "bg-success",
              }
            : undefined;
        return {
            thread: this.channel().thread,
            message: displayedMessage,
            counter: this.channel().importantCounter ?? this.channel().needactionCounter,
            datetime: displayedMessage?.datetime ?? this.channel().create_date,
            iconSrc: this.channel().thread.avatarUrl,
            important: !!(this.channel().importantCounter ?? this.channel().needactionCounter),
            isActive: this.isActive(),
            muted: this.channel().self_member_id?.mute_until_dt
                ? 2
                : !this.channel().isUnread
                ? 1
                : 0,
            nameMaxLine: 1,
            textMaxLine: 1,
            textTruncate: this.ui.isSmall,
            onSwipeRight: this.hasTouch() ? swipeRight : undefined,
            onSwipeLeft: this.swipeLeft ?? undefined,
            onClick: this.onClick,
        };
    },
    get prependNameWithStar() {
        return this.channel()?.self_member_id?.is_favorite;
    },
    get showActions() {
        return super.showActions || Boolean(this.channel());
    },
    get starTitle() {
        return _t("Favorite");
    },
    get swipeLeft() {
        if (this.hasTouch() && this.channel()?.canHide) {
            return {
                action: () => this.channel().unpinChannel(),
                icon: "fa-times-circle",
                bgColor: "bg-danger",
            };
        }
        return super.swipeLeft;
    },
});
