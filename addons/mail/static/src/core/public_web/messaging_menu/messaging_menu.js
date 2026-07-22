import { DiscussSearch } from "@mail/core/public_web/discuss_search";
import { MessageInDialog } from "@mail/core/public_web/messaging_menu/message_in_dialog";
import { MessagingMenuEmpty } from "@mail/core/public_web/messaging_menu/messaging_menu_empty";
import { MessagingMenuItem } from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import { useOnBottomScrolled, useSearch } from "@mail/utils/common/hooks";

import { Component, computed, signal, types, useEffect, useProps } from "@odoo/owl";

import { isDisplayStandalone, isIOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { normalize } from "@web/core/l10n/utils";
import { useService } from "@web/core/utils/hooks";

export class MessagingMenu extends Component {
    static components = { DiscussSearch, MessagingMenuItem, MessagingMenuEmpty };
    static template = "mail.MessagingMenu";

    isIosPwa = isIOS() && isDisplayStandalone();
    filteredMessages = computed(() => {
        const messages = this.activeTab().messages;
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
            types.signal(types.instanceOf(this.store.MessagingMenuUIState.Class))
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
    }

    get isEmpty() {
        return !this.messages().length;
    }

    get noSearchResultText() {
        return this.searchTerm() ? _t('No results for "%s".', this.searchTerm()) : "";
    }

    get noFilterResultText() {
        return _t("No conversation matches this filter.");
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
