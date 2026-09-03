import { DiscussSearch } from "@mail/core/public_web/discuss_search";
import { MessageInDialog } from "@mail/core/public_web/messaging_menu/message_in_dialog";
import { MessagingMenuEmpty } from "@mail/core/public_web/messaging_menu/messaging_menu_empty";
import { MessagingMenuItem } from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import { NotificationItem } from "@mail/core/public_web/notification_item";
import { useOnBottomScrolled, useSearch } from "@mail/utils/common/hooks";

import { Component, computed, signal, types, useEffect, useProps } from "@odoo/owl";

import { hasTouch, isDisplayStandalone, isIOS } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { normalize } from "@web/core/l10n/utils";
import { useService } from "@web/core/utils/hooks";

export class MessagingMenu extends Component {
    static components = {
        DiscussSearch,
        Dropdown,
        MessagingMenuItem,
        MessagingMenuEmpty,
        NotificationItem,
    };
    static template = "mail.MessagingMenu";

    isIosPwa = isIOS() && isDisplayStandalone();
    filteredMessages = computed(() => {
        const messages = this.activeTab().sortedMessages;
        if (!this.state().selectedFilter?.includesMessage) {
            return messages;
        }
        return messages.filter((m) => this.state().selectedFilter?.includesMessage(m));
    });
    messages = computed(() => {
        if (this.searchTerm()) {
            return this.messageSearch.results;
        }
        return this.filteredMessages();
    });
    searchTerm = signal("");
    tabContentRef = signal.ref();

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.notification = useService("mail.notification.permission");
        this.messageSearch = useSearch({
            fetch: (term) =>
                this.activeTab().loadMore({
                    filter: this.state().selectedFilter,
                    searchTerm: term,
                }),
            filter: (term) =>
                this.filteredMessages().filter((m) => {
                    const normalizedTerms = normalize(term);
                    return (
                        normalize(m.thread?.displayName).includes(normalizedTerms) ||
                        normalize(m.authorName).includes(normalizedTerms) ||
                        normalize(m.inlineBody).includes(normalizedTerms)
                    );
                }),
            deps: () => [this.filteredMessages()],
        });
        this.store = useService("mail.store");
        this.state = useProps.static(
            "state",
            types.signal(types.instanceOf(this.store.MessagingMenuUIState))
        );
        this.activeTab = computed(() => this.state().activeTab);
        this.close = useProps.static("close", types.function().optional());
        this.searchInputAutofocus = useProps.static(
            "searchInputAutofocus",
            types.signal(types.number()).optional()
        );
        this.ui = useService("ui");
        // Bound once so `onClickMessage` is a stable (useProps.static) handler.
        this.onClickMessage = this.onClickMessage.bind(this);
        useOnBottomScrolled(this.tabContentRef, () =>
            this.activeTab().loadMore({ filter: this.state().selectedFilter })
        );
        // On search term change: update the search state.
        useEffect(() => {
            this.messageSearch.searchTerm = this.searchTerm();
        });
        this.hasTouch = hasTouch;
    }

    get isEmpty() {
        return !this.messages().length && !this.showPushPermissionRequest;
    }

    get visibleTabs() {
        return this.store.messagingMenu.sortedVisibleTabs;
    }

    /** Counter shown on a tab's badge, if any. */
    getTabCounter(tab) {
        return tab.counter;
    }

    get noSearchResultText() {
        return this.searchTerm() ? _t('No results for "%s".', this.searchTerm()) : "";
    }

    get noFilterResultText() {
        return _t("No conversation matches this filter.");
    }

    /**
     * Whether the OdooBot extras (delivery failures, push permission request) may be
     * shown for the active tab.
     */
    get showNotificationHubExtras() {
        const menu = this.store.messagingMenu;
        return (
            !this.searchTerm() &&
            !this.state().selectedFilter &&
            this.state().activeTab.eq(menu.odooBotNotificationsTab)
        );
    }

    get showPushPermissionRequest() {
        return this.store.showPushPermissionRequest && this.showNotificationHubExtras;
    }

    get notificationRequest() {
        return {
            body: _t("Stay tuned! Enable push notifications to never miss a message."),
            displayName: _t("Turn on notifications"),
            partner: this.store.odoobot,
        };
    }

    /** @param {import("@mail/core/public_web/messaging_menu/messaging_menu_tab_model").MessagingMenuTabAction} action */
    onClickAction(action) {
        action.onClick();
        if (!action.preventDropdownClose) {
            this.close?.();
        }
    }

    /**
     * @param {import("models").Message} message
     * @param {Object} [param0]
     * @param {boolean} [param0.isMiddleClick] - Whether the click is a middle click or a ctrl+click.
     */
    onClickMessage(message, { isMiddleClick } = {}) {
        if (!message.thread) {
            this.dialog.add(MessageInDialog, { message });
            return;
        }
        message.thread.highlightMessage = message;
        message.thread
            .open({
                focus: true,
                fromMessagingMenu: true,
                bypassCompact: true,
                newWindow: isMiddleClick,
            })
            .then?.(() => {
                if (message.needaction) {
                    message.setDone();
                }
            })
            .catch((error) => {
                if (error.exceptionName === "odoo.exceptions.AccessError") {
                    this.dialog.add(MessageInDialog, { message });
                    return;
                }
                throw error;
            });
        this.close?.();
    }
}
