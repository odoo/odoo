import { Component, signal, types, useEffect, useProps } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";

export class DiscussSearch extends Component {
    static template = "mail.DiscussSearch";
    static components = {};

    searchInput = signal();

    setup() {
        this.props = useProps({
            autofocus: types.signal(types.number()).optional(),
            searchTerm: types.signal(types.string(), { settable: true }),
            class: types.or([types.string(), types.object()]).optional(),
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
            this.props.searchTerm.set("");
        }
    }

    onClearSearch() {
        this.props.searchTerm.set("");
    }
}
