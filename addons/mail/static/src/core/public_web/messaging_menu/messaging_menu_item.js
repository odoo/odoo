import { ActionList } from "@mail/core/common/action_list";
import { useMessageActions } from "@mail/core/common/message_actions";
import { Priority } from "@mail/core/common/priority";
import { NotificationItem } from "@mail/core/public_web/notification_item";
import { propSignal, useLongPress } from "@mail/utils/common/hooks";

import { Component, computed, props, signal, types } from "@odoo/owl";

import { hasTouch, isMobileOS } from "@web/core/browser/feature_detection";
import { DROPDOWN_NESTING } from "@web/core/dropdown/_behaviours/dropdown_nesting";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useChildSubEnv, useEnv } from "@web/owl2/utils";

const EXCLUDED_ACTIONS = new Set(["reaction", "reply-to"]);
const BOOKMARK_TAB_ACTIONS = new Set(["add-bookmark", "remove-bookmark", "copy-link"]);

export class MessagingMenuItem extends Component {
    static components = {
        ActionList,
        Dropdown,
        NotificationItem,
        Priority,
    };
    static template = "mail.MessagingMenuItem";

    isMobileOS = isMobileOS;
    root = signal();

    setup() {
        super.setup();
        // Sub-dropdowns (action menu, notification settings mute) closing should not
        // close the outer messaging menu dropdown via `closeAllParents()`. Must be here
        // rather than MessagingMenuInDropdown: the outer Dropdown overwrites
        // DROPDOWN_NESTING for its content, so a boundary set above it has no effect.
        const parentNesting = useEnv()[DROPDOWN_NESTING];
        if (parentNesting) {
            const boundary = Object.create(parentNesting);
            boundary.closeAllParents = () => {};
            useChildSubEnv({ [DROPDOWN_NESTING]: boundary });
        }
        this.store = useService("mail.store");
        this.message = props.static(
            "message",
            types.instanceOf(this.store["mail.message"].Class).optional()
        );
        this.activeTab = propSignal("activeTab", this.store["MessagingMenuTab"].Class);
        this.onClick = props.static("onClick", types.function());
        this.hasTouch = hasTouch;
        this.isActive = computed(() => this._isActive);
        this.messageActions = useMessageActions({
            message: () => this.message,
            thread: () => this.message?.thread,
        });
        this.messageDropdownState = useDropdownState();
        this.ui = useService("ui");
        useChildSubEnv({ inMessagingMenu: true });
        if (isMobileOS()) {
            useLongPress(this.root, {
                action: () => {
                    if (this.message) {
                        this.messageDropdownState.open();
                    }
                },
            });
        }
    }

    get _isActive() {
        return (
            this.store.discuss.isActive &&
            Boolean(this.message?.thread?.eq(this.store.discuss.thread))
        );
    }

    get actionsButtonClass() {
        return { "d-none": this.isMobileOS() };
    }

    get actionsButtonTitle() {
        return _t("Message Actions");
    }

    get actionsDropdownState() {
        return this.messageDropdownState;
    }

    get actionsPartition() {
        const { quick, other, group, actionPanels } = this.messageActions.partition;
        const isBookmarkTab = this.activeTab().eq(this.store.messagingMenu.bookmarkTab);
        const filter = (actions) =>
            actions.filter((a) =>
                isBookmarkTab ? BOOKMARK_TAB_ACTIONS.has(a.id) : !EXCLUDED_ACTIONS.has(a.id)
            );
        return {
            actionPanels,
            quick: filter(quick),
            other: filter(other),
            group: group.map(filter),
        };
    }

    get actionsTitle() {
        return _t("Thread Actions");
    }

    get attClass() {
        return {};
    }

    get itemName() {
        return this.message?.thread?.displayName ?? this.message?.authorName;
    }

    get itemPreviewText() {
        const message = this.notificationItemProps?.message ?? this.message;
        if (!message) {
            return _t("This is the start of your conversation");
        }
        if (!this.itemPreviewThread) {
            return message.isSelfAuthored ? message.previewText : message.bodyPreview;
        }
        return message.previewText;
    }

    get itemPreviewThread() {
        return this.message?.thread;
    }

    get notificationItemProps() {
        const menu = this.store.messagingMenu;
        const message = this.message;
        const activeTab = this.activeTab();
        // Distinct `eq()` instead of `in()` as `notificationTab` can be missing,
        // according to user preferences (i.e. "Handle by email").
        if (message && (activeTab.eq(menu.notificationTab) || activeTab.eq(menu.bookmarkTab))) {
            const isNotificationTab = this.activeTab().eq(menu.notificationTab);
            return {
                thread: message.thread,
                message,
                datetime: message?.datetime,
                iconSrc: message.authorAvatarUrl,
                important: isNotificationTab,
                isActive: this.isActive(),
                muted: message.needaction ? 0 : 1,
                textClassName: "text-truncate",
                onSwipeRight: isNotificationTab
                    ? {
                          action: () => this.message?.setDone(),
                          icon: "fa-check-circle",
                          bgColor: "bg-success",
                      }
                    : undefined,
                onClick: (isMarkAsRead, isMiddleClick) => this.onClick(message, { isMiddleClick }),
            };
        }
        return null;
    }

    get showActions() {
        return Boolean(this.message);
    }

    get swipeLeft() {
        return null;
    }
}
