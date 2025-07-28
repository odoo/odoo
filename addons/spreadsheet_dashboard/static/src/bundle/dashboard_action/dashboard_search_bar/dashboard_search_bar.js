import { Component, onWillUpdateProps, onWillStart, useState, status } from "@odoo/owl";
import { DashboardFacet } from "../dashboard_facet/dashboard_facet";
import { useService, useChildRef, useAutofocus } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DashboardDateFilter } from "../dashboard_date_filter/dashboard_date_filter";
import { FilterValuesList } from "@spreadsheet/global_filters/components/filter_values_list/filter_values_list";
import { getFacetInfo } from "@spreadsheet/global_filters/helpers";
import { _t } from "@web/core/l10n/translation";
import { fuzzyTest, fuzzyLookup } from "@web/core/utils/search";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { KeepLast } from "@web/core/utils/concurrency";

let nextItemId = 1;
const SUB_ITEMS_DEFAULT_LIMIT = 8;

export class DashboardSearchBar extends Component {
    static template = "spreadsheet_dashboard.DashboardSearchBar";
    static components = {
        DashboardFacet,
        DashboardDateFilter,
        FilterValuesList,
        Dropdown,
        DropdownItem,
    };
    static props = { model: Object };

    setup() {
        this.facets = [];
        this.firstDateFilter = undefined;
        this.nameService = useService("name");
        this.orm = useService("orm");
        this.keepLast = new KeepLast();
        this.fields = useService("field");

        this.inputRef = useAutofocus("autofocus");

        this.state = useState({
            showDropdown: false,
            expanded: [],
            query: "",
            subItemsLimits: {},
        });

        this.items = useState([]);
        this.subItems = {};

        this.filtersValuesDropdown = useDropdownState();
        this.inputDropdownState = useDropdownState();
        this.inputDropdownNavOptions = this.getDropdownNavigation();
        this.menuRef = useChildRef();
        onWillStart(this.computeState.bind(this));
        onWillUpdateProps(this.computeState.bind(this));
    }

    openFilterValueDropdown() {
        this.filtersValuesDropdown.open();
    }

    closeFilterValueDropdown() {
        this.filtersValuesDropdown.close();
    }

    toggleFilterValueDropdown() {
        this.filtersValuesDropdown.isOpen
            ? this.filtersValuesDropdown.close()
            : this.filtersValuesDropdown.open();
    }

    clearFilter(id) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", { id });
    }

    updateFirstDateFilter(value) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", {
            id: this.firstDateFilter.id,
            value,
        });
    }

    get firstDateFilterValue() {
        if (!this.firstDateFilter) {
            return undefined;
        }
        return this.props.model.getters.getGlobalFilterValue(this.firstDateFilter.id);
    }

    onSearchClick() {
        const query = this.inputRef?.el.value;
        if (query.trim()) {
            this.inputDropdownState.open();
            this.computeState({ query, expanded: [], subItems: [] });
        } else {
            this.inputDropdownState.close();
            this.resetState();
            this.filtersValuesDropdown.open();
        }
    }

    onSearchInput(ev) {
        const query = ev.target.value;
        if (query.trim()) {
            this.inputDropdownState.open();
            this.computeState({ query, expanded: [], subItems: [] });
        } else if (this.items.length) {
            this.inputDropdownState.close();
            this.resetState();
        }
    }

    onSearchInputKeydown(ev) {
        if (ev.key === "Backspace" || ev.key === "Delete") {
            const lastFacet = this.facets[this.facets.length - 1];
            if (ev.target.selectionStart === 0 && ev.target.selectionEnd === 0 && lastFacet) {
                this.clearFilter(lastFacet.id);
            }
        }
    }

    onSearchInputPointerDown(ev) {
        if (this.env.isSmall) {
            // Prevent the input from being focused on mobile, as it opens the keyboard
            ev.preventDefault();
        }
    }

    /**
     * @param {Object} [options={}]
     * @param {number[]} [options.expanded]
     * @param {string} [options.query]
     * @param {Object[]} [options.subItems]
     * @returns {Object[]}
     */
    async computeState(options = {}) {
        const query = "query" in options ? options.query : this.state.query;
        const expanded = "expanded" in options ? options.expanded : this.state.expanded;
        const subItems = "subItems" in options ? options.subItems : this.subItems;

        const tasks = [];
        for (const id of expanded) {
            if (!subItems[id]) {
                if (!this.state.subItemsLimits[id]) {
                    this.state.subItemsLimits[id] = SUB_ITEMS_DEFAULT_LIMIT;
                }
                tasks.push({ id, prom: this.computeSubItems(this.getGlobalFilter(id), query) });
            }
        }

        if (tasks.length) {
            const taskResults = await this.keepLast.add(
                Promise.all(tasks.map((task) => task.prom))
            );
            tasks.forEach((task, index) => {
                subItems[task.id] = taskResults[index];
            });
        }

        this.state.expanded = expanded;
        this.state.query = query;
        this.subItems = subItems;

        if (this.inputRef.el) {
            this.inputRef.el.value = query;
        }

        const filters = this.props.model.getters.getGlobalFilters();
        const firstDateFilterIndex = filters.findIndex((filter) => filter.type === "date");
        if (firstDateFilterIndex !== -1) {
            this.firstDateFilter = filters.splice(firstDateFilterIndex, 1)[0];
        }
        this.facets = await Promise.all(
            filters
                .filter((filter) => this.props.model.getters.isGlobalFilterActive(filter.id))
                .map((filter) => this.getFacetFor(filter))
        );

        this.items.length = 0;

        const trimmedQuery = this.state.query.trim();
        if (trimmedQuery) {
            for (const globalFilter of this.searchableGlobalFilters) {
                this.items.push(...this.getItems(globalFilter, trimmedQuery));
            }
        }
    }

    async getFacetFor(filter) {
        const filterValue = this.props.model.getters.getGlobalFilterValue(filter.id);
        return getFacetInfo(this.env, filter, filterValue);
    }

    getItems(globalFilter, trimmedQuery) {
        const items = [];

        if (globalFilter.type === "boolean") {
            const booleanOptions = [
                [true, _t("Yes")],
                [false, _t("No")],
            ];

            for (const [value, label] of booleanOptions) {
                if (fuzzyTest(trimmedQuery.toLowerCase(), label.toLowerCase())) {
                    items.push({
                        id: nextItemId++,
                        searchItemDescription: this.getTranslatedFilterLabel(globalFilter),
                        preposition: _t("for"),
                        globalFilterId: globalFilter.id,
                        label,
                        value,
                    });
                }
            }
            return items;
        }

        const isParent =
            globalFilter.type === "relation" ||
            globalFilter.type === "selection" ||
            this.getTextFilterAllowedValues(globalFilter);
        const isExpanded = isParent && this.state.expanded.includes(globalFilter.id);

        const item = {
            id: nextItemId++,
            searchItemDescription: this.getTranslatedFilterLabel(globalFilter),
            preposition: _t("for"),
            globalFilterId: globalFilter.id,
            label: this.state.query,
            value: trimmedQuery,
            unselectable: globalFilter.type === "selection",
            isParent,
            isExpanded,
        };

        items.push(item);

        if (item.isExpanded) {
            items.push(...this.subItems[globalFilter.id]);
        }

        return items;
    }

    getTextFilterAllowedValues(filter) {
        if (filter.type !== "text" || !filter.rangesOfAllowedValues?.length) {
            return undefined;
        }
        return this.props.model.getters.getTextFilterOptions(filter.id);
    }

    toggleItem(item, shouldExpand) {
        const expanded = [...this.state.expanded];
        const index = expanded.findIndex((id) => id === item.globalFilterId);
        if (shouldExpand === true && index < 0) {
            expanded.push(item.globalFilterId);
        } else if (shouldExpand === false && index >= 0) {
            expanded.splice(index, 1);
        }

        this.computeState({ expanded });
    }

    async computeSubItems(globalFilter, query) {
        let options = [];
        let showLoadMore = false;
        const limitToFetch = this.state.subItemsLimits[globalFilter.id] + 1;

        switch (globalFilter.type) {
            case "relation": {
                options = await this.orm.call(globalFilter.modelName, "name_search", [], {
                    domain: [],
                    context: {},
                    limit: limitToFetch,
                    name: query.trim(),
                });
                break;
            }
            case "text": {
                const allValues = this.getTextFilterAllowedValues(globalFilter) || [];
                options = fuzzyLookup(query, allValues, (value) => value.formattedValue).map(
                    (value) => [value.value, value.formattedValue]
                );
                break;
            }
            case "selection": {
                const { resModel, selectionField } = globalFilter;
                const fields = await this.fields.loadFields(resModel);
                const field = fields[selectionField];
                if (!field) {
                    throw new Error(`Field "${selectionField}" not found in model "${resModel}"`);
                }
                options = fuzzyLookup(query, field.selection, (value) => value[1]);
                break;
            }
        }

        if (options.length >= limitToFetch) {
            options = options.slice(0, limitToFetch);
            showLoadMore = true;
        }

        const subItems = [];
        if (options.length) {
            for (const [value, label] of options) {
                subItems.push({
                    id: nextItemId++,
                    isChild: true,
                    globalFilterId: globalFilter.id,
                    value,
                    label,
                });
            }
            if (showLoadMore) {
                subItems.push({
                    id: nextItemId++,
                    isChild: true,
                    globalFilterId: globalFilter.id,
                    label: _t("Load more"),
                    unselectable: true,
                    loadMore: () => {
                        this.state.subItemsLimits[globalFilter.id] += SUB_ITEMS_DEFAULT_LIMIT;
                        const newSubItems = [...this.subItems];
                        newSubItems[globalFilter.id] = undefined;
                        this.computeState({ subItems: newSubItems });
                    },
                });
            }
        } else {
            subItems.push({
                id: nextItemId++,
                isChild: true,
                globalFilterId: globalFilter.id,
                label: _t("(no result)"),
                unselectable: true,
            });
        }
        return subItems;
    }

    getGlobalFilter(id) {
        return this.props.model.getters.getGlobalFilter(id);
    }

    resetState(options = { focus: true }) {
        this.state.subItemsLimits = {};
        this.computeState({ expanded: [], query: "", subItems: [] });
        if (options.focus && !this.env.isSmall) {
            this.inputRef.el.focus();
        }
    }

    /**
     * @returns {import("@web/core/navigation/navigation").NavigationOptions}
     */
    getDropdownNavigation() {
        const isExpansible = (index) => {
            const item = this.items[index];
            return item && item.isParent;
        };

        const isCollapsible = (index) => {
            const item = this.items[index];
            return item && ((item.isParent && item.isExpanded) || item.isChild);
        };

        return {
            virtualFocus: true,
            getItems: () => this.menuRef.el?.querySelectorAll(":scope .o-dropdown-item") ?? [],
            isNavigationAvailable: ({ navigator, target }) => this.inputDropdownState.isOpen,
            onUpdated: (navigator) => (this.navigator = navigator),
            hotkeys: {
                escape: {
                    callback: () => {
                        this.inputDropdownState.close();
                        this.resetState();
                    },
                },
                arrowright: {
                    bypassEditableProtection: true,
                    allowRepeat: false,
                    isAvailable: ({ navigator }) => isExpansible(navigator.activeItemIndex),
                    callback: (navigator) => {
                        const item = this.items[navigator.activeItemIndex];
                        if (item.isParent) {
                            if (item.isExpanded) {
                                navigator.next();
                            } else {
                                this.toggleItem(item, true);
                            }
                        }
                    },
                },
                arrowleft: {
                    bypassEditableProtection: true,
                    isAvailable: ({ navigator }) => isCollapsible(navigator.activeItemIndex),
                    callback: (navigator) => {
                        const item = this.items[navigator.activeItemIndex];

                        const findIndex = (id) =>
                            this.items.findIndex(
                                (item) => item.isParent && item.globalFilterId === id
                            );
                        if (item && item.isParent && item.isExpanded) {
                            this.toggleItem(item, false);
                        } else if (item && item.isChild) {
                            navigator.items[findIndex(item.globalFilterId)]?.setActive();
                        }
                    },
                },
            },
        };
    }

    onInputDropdownChanged(isOpen) {
        if (!isOpen && status(this) === "mounted") {
            this.resetState({ focus: false });
        } else if (this.navigator) {
            this.navigator.items[0]?.setActive();
        }
    }

    get searchableGlobalFilters() {
        return this.props.model.getters
            .getGlobalFilters()
            .filter((filter) => filter.type !== "date" && filter.type !== "numeric");
    }

    getTranslatedFilterLabel(filter) {
        return _t(filter.label); // Label is extracted from the spreadsheet json file
    }

    selectItem(item) {
        if (item.loadMore) {
            item.loadMore();
            return;
        } else if (item.unselectable) {
            return;
        }

        const filter = this.getGlobalFilter(item.globalFilterId);
        const filterValue = this.props.model.getters.getGlobalFilterValue(filter.id);

        let newValue = undefined;
        switch (filter.type) {
            case "boolean":
                newValue = item.value === true ? { operator: "set" } : { operator: "not_set" };
                break;
            case "text": {
                const allowedValues = this.getTextFilterAllowedValues(filter)?.map((v) => v.value);
                if (allowedValues && !allowedValues.includes(item.value)) {
                    break;
                }
                const strings = filterValue?.strings || [];
                newValue = {
                    strings: [...strings, item.value],
                    operator: filterValue?.operator || "ilike",
                };
                break;
            }
            case "selection": {
                const selectionValues = filterValue?.selectionValues || [];
                newValue = {
                    selectionValues: [...selectionValues, item.value],
                    operator: filterValue?.operator || "in",
                };
                break;
            }
            case "relation": {
                const isILike = filterValue?.operator?.includes("ilike");
                if (item.isChild) {
                    const ids = filterValue?.ids || [];
                    newValue = {
                        ids: isILike ? [item.value] : [...ids, item.value],
                        operator: isILike ? "in" : filterValue?.operator || "in",
                    };
                } else {
                    const strings = filterValue?.strings || [];
                    newValue = {
                        strings: isILike ? [...strings, item.value] : [item.value],
                        operator: isILike ? "ilike" : filterValue?.operator || "ilike",
                    };
                }
                break;
            }
        }
        if (newValue) {
            this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", {
                id: filter.id,
                value: newValue,
            });
        }
        this.inputDropdownState.close();
        this.resetState();
    }
}
