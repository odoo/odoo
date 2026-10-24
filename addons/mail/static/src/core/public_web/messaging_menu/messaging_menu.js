import { DiscussSearch } from "@mail/core/public_web/discuss_search";
import { MessageInDialog } from "@mail/core/public_web/messaging_menu/message_in_dialog";
import { MessagingMenuEmpty } from "@mail/core/public_web/messaging_menu/messaging_menu_empty";
import { MessagingMenuItem } from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import { NotificationItem } from "@mail/core/public_web/notification_item";
import { htmlToTextContentInline } from "@mail/utils/common/format";
import { useOnBottomScrolled, usePeek, useSearch } from "@mail/utils/common/hooks";
import { computedShallowEqual, incrementFn } from "@mail/utils/common/signal";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

import { Component, computed, signal, types, useEffect, usePlugin, useProps } from "@odoo/owl";

import { hasTouch, isDisplayStandalone, isIOS } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { normalize } from "@web/core/l10n/utils";
import { usePopover } from "@web/core/popover/popover_hook";
import { UIPlugin } from "@web/core/ui/ui_plugin";
import { useAutofocus, useService } from "@web/core/utils/hooks";

/** Never a submenu of an ancestor Dropdown it's embedded in, even visually/positionally. */
class IsolatedDropdown extends Dropdown {
    get hasParent() {
        return false;
    }
}

class GuestNamePopover extends Component {
    static template = "mail.GuestNamePopover";

    inputRef = signal.ref();

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({ close: types.function().optional() });
        useAutofocus({ ref: this.inputRef });
    }

    /** @param {KeyboardEvent} ev */
    onKeydown(ev) {
        switch (ev.key) {
            case "Enter":
                // Commits the name through `change`.
                ev.target.blur();
                this.props.close?.();
                break;
            case "Escape":
                ev.target.value = this.store.self_guest.name;
                this.props.close?.();
                break;
        }
    }

    /** @param {string} name */
    async rename(name) {
        const newName = name.trim();
        if (newName && this.store.self_guest.name !== newName) {
            await this.store.self_guest.updateGuestName(newName);
        }
    }
}

export class MessagingMenu extends Component {
    static components = {
        DiscussSearch,
        IsolatedDropdown,
        MessagingMenuItem,
        MessagingMenuEmpty,
        NotificationItem,
    };
    static template = "mail.MessagingMenu";

    isIosPwa = isIOS() && isDisplayStandalone();
    isCollapsible = computed(() => this.ancestors.inDiscussApp && !this.ui.isSmall());
    /** Whether the list is hidden in the discuss sidebar, so that it shows over the content. */
    canPeek = computed(() => this.isCollapsible() && this.store.discuss.isSidebarCollapsed);
    /** @type {import("@odoo/owl").Signal<import("models").MessagingMenuUIState|undefined>} */
    peekedTabState = signal(undefined);
    /** The tab shown as active: the peeked one only has the look of a hovered tab. */
    selectedTab = computed(() => this.selectedState().activeTab);
    containerRef = signal.ref();
    filteredMessages = computedShallowEqual(() => {
        const filters = [...this.state().activePluginFilters];
        if (this.state().selectedFilter) {
            filters.push(this.state().selectedFilter);
        }
        const messages = this.activeTab().sortedMessages;
        return messages.filter((m) =>
            filters.every((f) => !f.includesMessage || f.includesMessage(m))
        );
    });
    messages = computed(() => {
        if (this.state().searchTerm) {
            return this.messageSearch.results;
        }
        return this.filteredMessages();
    });
    tabContentRef = signal.ref();

    setup() {
        super.setup();
        this.ancestors = useAncestors();
        this.dialog = useService("dialog");
        this.notification = useService("mail.notification.permission");
        this.store = useService("mail.store");
        this.selectedState = useProps.static(
            "state",
            types.signal(types.instanceOf(this.store.MessagingMenuUIState))
        );
        /** The state of the shown list: the one of the peeked tab, if any. */
        this.state = computed(() => this.peekedTabState() ?? this.selectedState());
        this.activeTab = computed(() => this.state().activeTab);
        this.messageSearch = useSearch({
            fetch: (term) =>
                this.activeTab().loadMore({
                    filter: this.state().selectedFilter,
                    pluginFilters: this.state().activePluginFilters,
                    searchTerm: term,
                }),
            filter: (term) =>
                this.filteredMessages().filter((m) => {
                    const normalizedTerms = normalize(term);
                    return (
                        normalize(m.thread?.displayName).includes(normalizedTerms) ||
                        normalize(m.authorName).includes(normalizedTerms) ||
                        normalize(htmlToTextContentInline(m.inlineBody)).includes(normalizedTerms)
                    );
                }),
            deps: () => [this.filteredMessages()],
        });
        this.close = useProps.static("close", types.function().optional());
        this.onToggleSidebar = useProps.static("onToggleSidebar", types.function().optional());
        this.searchInputAutofocus = useProps.static(
            "searchInputAutofocus",
            types.signal(types.number()).optional(() => signal(0))
        );
        this.focusSearchInput = incrementFn(this.searchInputAutofocus);
        this.ui = usePlugin(UIPlugin);
        // Bound once so `onClickMessage` is a stable (useProps.static) handler.
        this.onClickMessage = this.onClickMessage.bind(this);
        useOnBottomScrolled(this.tabContentRef, () =>
            this.activeTab().loadMore({
                filter: this.state().selectedFilter,
                pluginFilters: this.state().activePluginFilters,
            })
        );
        // On search term change: update the search state.
        useEffect(() => {
            this.messageSearch.searchTerm = this.state().searchTerm;
        });
        this.hasTouch = hasTouch;
        // The whole sidebar of the discuss app peeks, with the handle that resizes the list.
        const peekRef = () =>
            this.containerRef()?.closest(".o-mail-DiscussApp-sidebar") ?? this.containerRef();
        this.peek = usePeek(peekRef, {
            enabled: () => this.canPeek(),
            keep: () => Boolean(this.state().searchTerm),
            onClose: () => {
                this.clearPeekedTab();
                this.selectedState().searchTerm = "";
            },
        });
        this.guestNamePopover = usePopover(GuestNamePopover, {
            arrow: false,
            position: "right-end",
        });
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
        return this.state().searchTerm ? _t('No results for "%s".', this.state().searchTerm) : "";
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
            !this.state().searchTerm &&
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

    toggleSidebarTitle() {
        return this.store.discuss.isSidebarCollapsed
            ? _t("Expand sidebar")
            : _t("Collapse sidebar");
    }

    /**
     * Shows the list of the tab over the content, without selecting it: that would close the
     * conversation.
     *
     * @param {import("models").MessagingMenuTab} tab
     */
    peekTab(tab) {
        if (!this.canPeek()) {
            return;
        }
        if (tab.eq(this.selectedTab())) {
            this.clearPeekedTab();
        } else if (this.peekedTabState()) {
            this.peekedTabState().activeTab = tab;
        } else {
            this.peekedTabState.set(
                this.store.MessagingMenuUIState.insert({
                    id: `${this.selectedState().id}.peek`,
                    activeTab: tab,
                })
            );
        }
    }

    clearPeekedTab() {
        const peekedTabState = this.peekedTabState();
        this.peekedTabState.set(undefined);
        peekedTabState?.delete();
    }

    onClickToggleSidebar() {
        this.peek.close();
        this.onToggleSidebar();
        this.peek.openIfHovered();
    }

    /** @param {MouseEvent} ev */
    onClickSelf(ev) {
        if (this.guestNamePopover.isOpen) {
            this.guestNamePopover.close();
        } else {
            this.guestNamePopover.open(ev.currentTarget, {});
        }
    }

    /**
     * @param {PointerEvent} ev
     * @param {import("models").MessagingMenuTab} tab
     */
    onClickTab(ev, tab) {
        if (this.canPeek() && (ev.pointerType === "touch" || ev.pointerType === "pen")) {
            this.peekTab(tab);
            this.peek.open();
            return;
        }
        this.clearPeekedTab();
        this.selectedState().selectTab(tab);
        if (this.canPeek()) {
            this.peek.open();
        }
    }

    /** A conversation of the list is opened in the content. */
    onOpenConversation() {
        if (!this.peek.isOpen()) {
            return;
        }
        this.selectedState().activeTab = this.activeTab();
        this.peek.closeOnceLeft();
    }

    /**
     * @param {FocusEvent} ev
     * @param {import("models").MessagingMenuTab} tab
     */
    onFocusTab(ev, tab) {
        if (ev.target.matches(":focus-visible")) {
            this.peekTab(tab);
        }
    }

    /**
     * @param {PointerEvent} ev
     * @param {import("models").MessagingMenuTab} tab
     */
    onPointerenterTab(ev, tab) {
        if (ev.pointerType === "mouse") {
            this.peekTab(tab);
        }
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
        if (!isMiddleClick) {
            this.onOpenConversation();
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
