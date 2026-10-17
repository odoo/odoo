import { DiscussSearch } from "@mail/core/public_web/discuss_search";
import { MessageInDialog } from "@mail/core/public_web/messaging_menu/message_in_dialog";
import { MessagingMenuEmpty } from "@mail/core/public_web/messaging_menu/messaging_menu_empty";
import { MessagingMenuItem } from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import { NotificationItem } from "@mail/core/public_web/notification_item";
import { useOnBottomScrolled, useSearch } from "@mail/utils/common/hooks";
import { computedShallowEqual, incrementFn } from "@mail/utils/common/signal";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

import { Component, computed, onWillUnmount, signal, types, useEffect, useProps } from "@odoo/owl";

import { hasTouch, isDisplayStandalone, isIOS } from "@web/core/browser/feature_detection";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { normalize } from "@web/core/l10n/utils";
import { useService } from "@web/core/utils/hooks";

export const PEEK_DELAY = 150;

/** Never a submenu of an ancestor Dropdown it's embedded in, even visually/positionally. */
class IsolatedDropdown extends Dropdown {
    get hasParent() {
        return false;
    }
}

export class MessagingMenu extends Component {
    static components = {
        CheckboxItem,
        DiscussSearch,
        IsolatedDropdown,
        MessagingMenuItem,
        MessagingMenuEmpty,
        NotificationItem,
    };
    static template = "mail.MessagingMenu";

    isIosPwa = isIOS() && isDisplayStandalone();
    isCollapsible = computed(() => this.ancestors.inDiscussApp && !this.ui.isSmall);
    isCompact = computed(
        () => this.isCollapsible() && this.store.discuss.isSidebarCollapsed && !this.isPeeking()
    );
    isPeeking = signal(false);
    /**
     * Filters that do not fit in the row of the discuss sidebar, offered in "More" instead;
     * `undefined` stands for "All".
     *
     * @type {import("@odoo/owl").Signal<Array<import("models").MessagingMenuTabFilter|undefined>>}
     */
    overflowFilters = signal([]);
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
    filtersRef = signal.ref();
    tabContentRef = signal.ref();

    setup() {
        super.setup();
        this.ancestors = useAncestors();
        this.dialog = useService("dialog");
        this.notification = useService("mail.notification.permission");
        this.store = useService("mail.store");
        this.state = useProps.static(
            "state",
            types.signal(types.instanceOf(this.store.MessagingMenuUIState))
        );
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
                        normalize(m.inlineBody).includes(normalizedTerms)
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
        this.ui = useService("ui");
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
        // Opening the filters from the strip of avatars shows the full list.
        this.filterDropdownState = useDropdownState({
            onOpen: () => {
                clearTimeout(this.peekTimeout);
                this.isPeeking.set(true);
            },
        });
        onWillUnmount(() => clearTimeout(this.peekTimeout));
        useEffect(() => {
            const filtersEl = this.filtersRef();
            if (!filtersEl || !this.isCollapsible()) {
                return;
            }
            void [this.activeTab().sortedFilters, this.state().selectedFilter];
            const observer = new ResizeObserver(() => this.updateOverflowFilters(filtersEl));
            for (const el of [filtersEl, ...filtersEl.children]) {
                observer.observe(el);
            }
            return () => observer.disconnect();
        });
    }

    allFilterText() {
        return _t("All");
    }

    filterToggleTitle() {
        return _t("Filter: %s", this.state().selectedFilter?.text ?? this.allFilterText());
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

    closePeek() {
        clearTimeout(this.peekTimeout);
        this.isPeeking.set(false);
        this.filterDropdownState.close();
    }

    onClickToggleSidebar() {
        this.closePeek();
        this.onToggleSidebar();
    }

    onMouseenter() {
        if (this.isCompact()) {
            clearTimeout(this.peekTimeout);
            this.peekTimeout = setTimeout(() => this.isPeeking.set(true), PEEK_DELAY);
        }
    }

    /** @param {MouseEvent} ev */
    onMouseleave(ev) {
        // Keep the list while using one of its dropdowns.
        if (!ev.relatedTarget?.closest?.(".o-overlay-container")) {
            this.closePeek();
        }
    }

    /**
     * Keeps in the row the filters that fit, the selected one always among them.
     *
     * @param {HTMLElement} filtersEl
     */
    updateOverflowFilters(filtersEl) {
        const filters = [undefined, ...this.activeTab().sortedFilters];
        const chips = filtersEl.querySelectorAll(":scope > .o-mail-MessagingMenu-filter");
        const gap = parseFloat(getComputedStyle(filtersEl).columnGap) || 0;
        const widths = [...chips].map((chip) => chip.offsetWidth + gap);
        /** @param {number} available */
        const countFitting = (available) => {
            let count = 0;
            let used = 0;
            for (const width of widths) {
                used += width;
                if (used > available + gap) {
                    break;
                }
                count++;
            }
            return count;
        };
        let count = countFitting(filtersEl.clientWidth);
        if (count < filters.length) {
            const moreEl = filtersEl.querySelector(".o-mail-MessagingMenu-filterMore");
            count = Math.max(countFitting(filtersEl.clientWidth - moreEl.offsetWidth - gap), 1);
        }
        const fitting = filters.slice(0, count);
        const selected = this.state().selectedFilter;
        if (!fitting.includes(selected)) {
            fitting[count - 1] = selected;
        }
        const overflow = filters.filter((filter) => !fitting.includes(filter));
        const previous = this.overflowFilters();
        if (
            overflow.length !== previous.length ||
            overflow.some((filter, index) => filter !== previous[index])
        ) {
            this.overflowFilters.set(overflow);
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
