import { onWillRender, useRef, useState } from "@web/owl2/utils";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { fuzzyLookup } from "@web/core/utils/search";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";

const INITIAL_SEARCH_LIMIT = 8;

export class OfflineSearchBar extends Component {
    static template = "web.OfflineSearchBar";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        autofocus: { type: Boolean, optional: true },
        toggler: { type: Object, optional: true },
    };

    setup() {
        this.ui = useService("ui");
        this.rootRef = useRef("root");
        this.inputRef =
            this.env.config.disableSearchBarAutofocus || !this.props.autofocus
                ? useRef("autofocus")
                : useAutofocus({ mobile: this.ui.isSmall }); // only force the focus on touch devices on small screens
        this.searchBarDropdownState = useDropdownState();
        this.visibilityState = useState(this.props.toggler?.state || { showSearchBar: true });

        useHotkey("backspace", () => this.onBackspace(), {
            area: () => this.inputRef.el,
            bypassEditableProtection: true,
            isAvailable: () => this.inputRef.el.value === "",
        });

        this.allSearches = [];
        this.state = useState({
            searches: [],
            limit: INITIAL_SEARCH_LIMIT,
        });

        const offlineService = useService("offline");
        onWillStart(async () => {
            const { actionId, viewType } = this.env.config;
            this.allSearches = await offlineService.getAvailableSearches(actionId, viewType);
            this.emptySearch = this.allSearches.find((search) => !search.facets.length) || null;
            this.state.searches = this.allSearches;
        });

        onWillRender(() => {
            const currentSearch = this.env.searchModel.getCurrentSearch();
            this.currentSearch =
                this.allSearches.find((search) => search.key === currentSearch.key) ||
                currentSearch;
        });
    }

    get isSearchMenuDisabled() {
        return (
            this.allSearches.length === 0 || (this.allSearches.length === 1 && !!this.emptySearch)
        );
    }

    canRemoveSearch() {
        return (
            this.currentSearch.facets.length &&
            (this.emptySearch ||
                (this.allSearches.length && this.currentSearch.key !== this.allSearches[0].key))
        );
    }

    selectSearch(search) {
        this.state.value = search.key;
        this.env.searchModel.applySearch(search);
    }

    onBackspace() {
        if (this.emptySearch && this.inputRef.el.value === "") {
            this.selectSearch(this.emptySearch);
        }
    }

    onRemoveSearch() {
        this.selectSearch(this.emptySearch || this.allSearches[0]);
    }

    onSearchInput(ev) {
        const query = ev.target.value;
        if (!query) {
            this.state.searches = this.allSearches;
        } else {
            this.state.searches = fuzzyLookup(query, this.allSearches, ({ facets }) =>
                facets.map((f) => (f.type === "field" ? f.title : "") + f.values.join("")).join("")
            );
        }
        if (!this.state.searches.length) {
            this.searchBarDropdownState.close();
        } else {
            this.searchBarDropdownState.open();
        }
    }

    onSelect(search) {
        this.inputRef.el.value = "";
        this.selectSearch(search);
    }

    onShowMoreSearches() {
        this.state.limit += INITIAL_SEARCH_LIMIT;
    }
}
