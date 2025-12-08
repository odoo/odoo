import { useService } from "@web/core/utils/hooks";
import { onWillRender, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { SearchBar } from "./search_bar";
import { fuzzyLookup } from "@web/core/utils/search";
import { groupBy, sortBy } from "@web/core/utils/arrays";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";

const INITIAL_FILTER_LIMIT = 8;
export class OfflineSearchBar extends SearchBar {
    static template = "web.OfflineSearchBar";
    static components = {
        ...SearchBar.components,
        Dropdown,
        DropdownItem,
    };

    setup() {
        super.setup();
        this.offlineUI = useService("offline_ui");
        this.rootRef = useRef("root");

        useHotkey("backspace", () => this.onBackspace(), {
            area: () => this.inputRef.el,
            bypassEditableProtection: true,
            isAvailable: () => this.inputRef.el.value === "",
        });
        const { actionId, viewType } = this.env.config;
        const filters = Object.entries(this.offlineUI.visited[actionId]?.views[viewType] || {})
            .map(([query, { facets, count }]) => ({ query, facets: facets, count }))
            .reverse(); // last visited first
        const { true: nonEmptyFilters, false: emptyFilters } = groupBy(
            filters,
            (filter) => !!filter.facets.length
        );
        this.emptyFilter = emptyFilters?.[0] || null;
        this.filters = sortBy(nonEmptyFilters || [], (filter) => filter.count, "desc");
        this.state = useState({
            filters: this.filters,
            limit: INITIAL_FILTER_LIMIT,
        });
        if (filters.length <= 1) {
            this.visibilityState = { showSearchBar: false };
        }

        onWillRender(() => {
            const currentQuery = JSON.stringify(this.env.searchModel.query);
            this.currentFilter = this.filters.find(({ query }) => query === currentQuery);
        });
    }

    setupFacetNavigation() {} // disable facet navigation

    canRemoveFilter() {
        return (
            this.currentFilter?.facets.length &&
            (this.emptyFilter || this.currentFilter !== this.filters[0])
        );
    }

    selectFilter(filter) {
        this.state.value = filter.query;
        this.env.searchModel.query = JSON.parse(filter.query);
        this.env.searchModel._notify();
    }

    onBackspace() {
        if (this.emptyFilter && this.inputRef.el.value === "") {
            this.selectFilter(this.emptyFilter);
        }
    }

    onClickSearchIcon() {
        this.env.searchModel.search();
    }

    onRemoveFilter() {
        this.selectFilter(this.emptyFilter || this.filters[0]);
    }

    onSearchInput(ev) {
        const query = ev.target.value;
        if (!query) {
            this.state.filters = this.filters;
        } else {
            this.state.filters = fuzzyLookup(ev.target.value, this.filters, ({ facets }) =>
                facets
                    .map(
                        (facet) =>
                            (facet.type === "field" ? facet.title : "") + facet.values.join("")
                    )
                    .join("")
            );
        }
        if (!this.state.filters.length) {
            this.searchBarDropdownState.close();
        } else {
            this.searchBarDropdownState.open();
        }
    }

    onSelect(filter) {
        this.inputRef.el.value = "";
        this.selectFilter(filter);
    }

    onShowMoreFilters() {
        this.state.limit += INITIAL_FILTER_LIMIT;
    }
}
