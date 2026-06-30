import { propSignal } from "@mail/utils/common/hooks";
import { Component, props, signal, types, useEffect } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

export class DiscussSearch extends Component {
    static template = "mail.DiscussSearch";
    static components = {};

    searchInput = signal();

    setup() {
        this.autofocus = propSignal("autofocus", types.number(), { optional: true });
        this.searchTerm = propSignal("searchTerm", types.string());
        this.props = props({
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
            this.searchTerm.set("");
        }
    }

    onClearSearch() {
        this.searchTerm.set("");
    }
}
