import { propSignal } from "@mail/utils/common/hooks";
import { Component, signal, types, useEffect, useProps } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";
import { useService } from "@web/core/utils/hooks";

export class DiscussSearch extends Component {
    static template = "mail.DiscussSearch";
    static components = {};

    searchInput = signal();

    setup() {
        this.store = useService("mail.store");
        this.autofocus = propSignal("autofocus", types.number(), { optional: true });
        this.messagingMenuUiState = propSignal(
            "messagingMenuUiState",
            types.instanceOf(this.store.MessagingMenuUIState)
        );
        this.props = useProps({
            class: types.or([types.string(), types.object()]).optional(),
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
            this.messagingMenuUiState().searchTerm = "";
        }
    }

    onClearSearch() {
        this.messagingMenuUiState().searchTerm = "";
    }
}
