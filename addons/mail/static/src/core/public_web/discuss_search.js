<<<<<<< 2cee9b56ec47892a262abadf6aad7f04101537d2
import { SearchInput } from "@mail/core/common/search_input";
import { propSignal, useSearch } from "@mail/utils/common/hooks";
import { Component, signal, types, useEffect, useProps } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";
||||||| 83d8e35a2387c3867b316e6065c5d8b4205ae376
import { useHover } from "@mail/utils/common/hooks";
import { Component, props, t } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
=======
import { useHover, UseHoverOverlay } from "@mail/utils/common/hooks";
import { Component, props, t } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
>>>>>>> a0eeb24a8a78713cbf37bdf98a60e6825fc17dc6
import { useService } from "@web/core/utils/hooks";

export class DiscussSearch extends Component {
    static template = "mail.DiscussSearch";
<<<<<<< 2cee9b56ec47892a262abadf6aad7f04101537d2
    static components = { SearchInput };

    searchInput = signal.ref();
||||||| 83d8e35a2387c3867b316e6065c5d8b4205ae376
    static components = { Dropdown };
=======
    static components = { Dropdown, UseHoverOverlay };
>>>>>>> a0eeb24a8a78713cbf37bdf98a60e6825fc17dc6

    setup() {
        this.store = useService("mail.store");
<<<<<<< 2cee9b56ec47892a262abadf6aad7f04101537d2
        this.autofocus = propSignal("autofocus", types.number(), { optional: true });
        this.messagingMenuUiState = propSignal(
            "messagingMenuUiState",
            types.instanceOf(this.store.MessagingMenuUIState)
        );
        this.props = useProps({
            class: types.or([types.string(), types.object()]).optional(),
||||||| 83d8e35a2387c3867b316e6065c5d8b4205ae376
        this.command = useService("command");
        this.ui = useService("ui");
        this.searchHover = useHover(["search-btn", "search-floating"], {
            onHover: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.searchFloating.isOpen = true;
                }
            },
            onAway: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.searchFloating.isOpen = false;
                }
            },
=======
        this.command = useService("command");
        this.ui = useService("ui");
        this.searchHover = useHover(["search-btn"], {
            onHover: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.searchFloating.isOpen = true;
                }
            },
            onAway: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.searchFloating.isOpen = false;
                }
            },
>>>>>>> a0eeb24a8a78713cbf37bdf98a60e6825fc17dc6
        });
        this.search = useSearch({
            searchTerm: this.messagingMenuUiState()._.fieldsAttrSignal.get("searchTerm"),
        });
        useEffect(() => {
            if (this.autofocus?.()) {
                this.searchInput()?.focus();
            }
        });
    }

    get class() {
        if (typeof this.props.class === "object" && this.props.class !== null) {
            return Object.entries(this.props.class)
                .filter(([_, val]) => val)
                .map(([key, _]) => key)
                .join(" ");
        }
        return this.props.class;
    }

    onKeydownSearch(ev) {
        if (getActiveHotkey(ev) === "escape") {
            ev.stopPropagation();
            ev.preventDefault();
            this.onClearSearch();
        }
    }

<<<<<<< 2cee9b56ec47892a262abadf6aad7f04101537d2
    onClearSearch() {
        this.search.searchTerm = "";
||||||| 83d8e35a2387c3867b316e6065c5d8b4205ae376
    onClickSearchConversations() {
        this.command.openMainPalette({ searchValue: "@" });
=======
    onClickSearchConversations() {
        this.searchFloating.close();
        this.command.openMainPalette({ searchValue: "@" });
>>>>>>> a0eeb24a8a78713cbf37bdf98a60e6825fc17dc6
    }
}
