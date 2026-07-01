import { DiscussSearch } from "@mail/core/public_web/discuss_search";
import { MessageDialog } from "@mail/core/public_web/messaging_menu/message_dialog";
import { MessagingMenuEmpty } from "@mail/core/public_web/messaging_menu/messaging_menu_empty";
import { MessagingMenuItem } from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import { propComputed, useOnBottomScrolled, useSearch } from "@mail/utils/common/hooks";

import { Component, computed, props, signal, types, useEffect } from "@odoo/owl";

import { isDisplayStandalone, isIOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { normalize } from "@web/core/l10n/utils";
import { useService } from "@web/core/utils/hooks";

export class MessagingMenu extends Component {
    static components = { DiscussSearch, MessagingMenuItem, MessagingMenuEmpty };
    static template = "mail.MessagingMenu";

    isIosPwa = isIOS() && isDisplayStandalone();
    filteredMessages = computed(() => {
        const messages = this.state().activeTab.messages;
        if (!this.state().selectedFilter?.matchesMessage) {
            return messages;
        }
        return messages.filter((m) => this.state().selectedFilter?.matchesMessage(m));
    });
    messages = computed(() => {
        if (this.searchTerm()) {
            return this.messageSearch.results;
        }
        return this.filteredMessages();
    });
    searchTerm = signal("");

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.messageSearch = useSearch({
            fetch: (term) =>
                this.state().activeTab.loadMore({
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
        this.state = propComputed("state", types.instanceOf(this.store.MessagingMenuState.Class));
        this.close = props.static("close", types.function().optional());
        this.searchInputAutofocus = props.static(
            "searchInputAutofocus",
            types.signal(types.number()).optional()
        );
        this.ui = useService("ui");
        useOnBottomScrolled("tabContent", () =>
            this.state().activeTab.loadMore({ filter: this.state().selectedFilter })
        );
        // On search term change: update the search state.
        useEffect(() => {
            this.messageSearch.searchTerm = this.searchTerm();
        });
    }

    get navigationAtBottom() {
        return this.ui.isSmall;
    }

    get isEmpty() {
        return !this.messages().length;
    }

    get noSearchResultText() {
        return this.searchTerm() ? _t('No results for "%s".', this.searchTerm()) : "";
    }

    onClickAction(action) {
        action.onClick();
        this.close?.();
    }

    onClickMessage(message) {
        if (!message.thread) {
            this.dialog.add(MessageDialog, { message });
            return;
        }
        if (message.needaction) {
            message.setDone();
        }
        message.thread.highlightMessage = message;
        message.thread
            .open({ focus: true, fromMessagingMenu: true, bypassCompact: true })
            .then?.(() => {
                if (message.needaction) {
                    message.setDone();
                }
            })
            .catch((error) => {
                if (error.exceptionName === "odoo.exceptions.AccessError") {
                    this.dialog.add(MessageDialog, { message });
                }
            });
        this.close?.();
    }

    onNavbarWheel(ev) {
        ev.currentTarget.scrollLeft += ev.deltaY;
    }
}
