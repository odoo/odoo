import { SearchInput } from "@mail/core/common/search_input";
import { useSearch } from "@mail/utils/common/hooks";
import { Component, signal, types, useEffect, useProps } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";
import { useService } from "@web/core/utils/hooks";

export class DiscussSearch extends Component {
    static template = "mail.DiscussSearch";
    static components = { SearchInput };

    searchInput = signal.ref();

    setup() {
        this.store = useService("mail.store");
        this.props = useProps({
            autofocus: types.signal(types.number()).optional(),
            class: types.or([types.string(), types.object()]).optional(),
            messagingMenuUiState: types.signal(types.instanceOf(this.store.MessagingMenuUIState)),
        });
        this.search = useSearch({
            searchTerm: this.props.messagingMenuUiState()._.fieldsAttrSignal.get("searchTerm"),
        });
        useEffect(() => {
            if (this.props.autofocus?.()) {
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

    onClearSearch() {
        this.search.searchTerm = "";
    }
}
