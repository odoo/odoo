// @ts-check
/** @odoo-module native */

import { Component, status, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { useDropdownState } from "@web/components/dropdown/dropdown_hook";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { hasTouch } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { Domain } from "@web/core/domain";
import { SearchModelEvent } from "@web/core/events";
import { getFieldCodec } from "@web/core/field_codec";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { useNavigation } from "@web/core/navigation/navigation";
import { _t } from "@web/core/translation";
import { KeepLast, SupersededError } from "@web/core/utils/concurrency";
import { useAutofocus, useBus, useChildRef, useService } from "@web/core/utils/hooks";
import { fuzzyTest } from "@web/core/utils/search";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";

const parseValue = (value, fieldType) => {
    const parser = getFieldCodec(fieldType).parse;
    switch (fieldType) {
        case "date": {
            return serializeDate(parser(value));
        }
        case "datetime": {
            return serializeDateTime(parser(value));
        }
        case "many2one": {
            return value;
        }
        default: {
            return parser(value);
        }
    }
};

const CHAR_FIELDS = [
    "char",
    "html",
    "many2many",
    "many2one",
    "one2many",
    "text",
    "properties",
];
const FOLDABLE_TYPES = ["properties", "many2one", "many2many"];

let nextItemId = 1;
const SUB_ITEMS_DEFAULT_LIMIT = 8;

const log = makeLogger("web.search.bar");

export class SearchBar extends Component {
    static template = "web.SearchBar";
    static components = {
        SearchBarMenu,
        Dropdown,
        DropdownItem,
    };
    static props = {
        autofocus: { type: Boolean, optional: true },
        slots: {
            type: Object,
            optional: true,
            shape: {
                default: { optional: true },
                "search-bar-additional-menu": { optional: true },
            },
        },
        toggler: {
            type: Object,
            optional: true,
        },
    };
    static defaultProps = {
        autofocus: true,
    };

    /** @type {{ el: HTMLElement | null }} */
    root;
    /** @type {import("services").ServiceFactories["ui"]} */
    ui;
    /** @type {{ showSearchBar: boolean }} */
    visibilityState;
    /**
     * @type {{
     * expanded: any[];
     * query: string;
     * subItemsLimits: Record<string, number>;
     * }}
     */
    state;
    /** @type {any[]} */
    items;
    /** @type {Record<string, any>} */
    subItems;
    /** @type {{ el: HTMLElement | null }} */
    facetContainerRef;
    /** @type {ReturnType<typeof useChildRef>} */
    menuRef;
    /** @type {ReturnType<typeof useDropdownState>} */
    inputDropdownState;
    /** @type {ReturnType<SearchBar["getDropdownNavigation"]>} */
    inputDropdownNavOptions;
    /** @type {ReturnType<typeof useDropdownState>} */
    searchBarDropdownState;
    /** @type {import("services").ServiceFactories["orm"]} */
    orm;
    /** @type {KeepLast<any>} */
    keepLast;
    /** @type {Map<string, Promise<any>>} */
    _pendingSubItems;
    /** @type {{ el: HTMLElement | null }} */
    inputRef;

    setup() {
        useLifecycleLog(log);
        this.root = useRef("root");
        this.ui = useService("ui");

        this.visibilityState = useState(
            this.props.toggler?.state || { showSearchBar: true },
        );

        this.state = useState({
            expanded: [],
            query: "",
            subItemsLimits: {},
        });

        this.items = useState([]);
        this.subItems = {};

        this.facetContainerRef = useRef("facetContainerRef");
        this.menuRef = useChildRef();
        this.setupFacetNavigation();
        this.inputDropdownState = useDropdownState();
        this.inputDropdownNavOptions = this.getDropdownNavigation();

        this.searchBarDropdownState = useDropdownState();

        this.orm = useService("orm");

        this.keepLast = new KeepLast({ rejectSuperseded: true });
        this._pendingSubItems = new Map();

        this.inputRef =
            this.env.config.disableSearchBarAutofocus || !this.props.autofocus
                ? useRef("autofocus")
                : useAutofocus({ mobile: this.ui.isSmall });

        useBus(this.env.searchModel, SearchModelEvent.FOCUS_SEARCH, () => {
            this.inputRef.el?.focus();
        });

        useBus(this.env.searchModel, SearchModelEvent.UPDATE, () => this.render());
    }

    get searchItemsFields() {
        return this.env.searchModel.getSearchItems((f) => f.type === "field");
    }

    /** @returns {Record<string, Object>} */
    get fields() {
        return this.env.searchModel.searchViewFields;
    }

    /** @param {number} id */
    getSearchItem(id) {
        return this.env.searchModel.searchItems[id];
    }

    /**
     * @param {object} [options={}]
     * @param {number[]} [options.expanded]
     * @param {string} [options.query]
     * @param {Record<number, Object[]>} [options.subItems]
     * @returns {Promise<void>}
     */
    async computeState(options = {}) {
        const query =
            "query" in options
                ? /** @type {string} */ (options.query)
                : this.state.query;
        const subItems =
            "subItems" in options
                ? /** @type {Record<number, Object[]>} */ (options.subItems)
                : this.subItems;
        const expanded = (
            "expanded" in options
                ? /** @type {number[]} */ (options.expanded)
                : this.state.expanded
        ).filter((id) => {
            const searchItem = this.getSearchItem(id);
            return searchItem && this.getFieldType(searchItem) !== undefined;
        });

        const tasks = [];
        for (const id of expanded) {
            const searchItem = this.getSearchItem(id);
            if (searchItem.type === "field" && searchItem.fieldType === "properties") {
                tasks.push({
                    id,
                    prom: this.env.searchModel
                        .getSearchItemsProperties(searchItem)
                        .catch(() => []),
                });
            } else if (!subItems[id]) {
                if (!this.state.subItemsLimits[id]) {
                    this.state.subItemsLimits[id] = SUB_ITEMS_DEFAULT_LIMIT;
                }
                tasks.push({
                    id,
                    prom: this._getSubItems(searchItem, query),
                });
            }
        }

        let taskResults;
        try {
            taskResults = await this.keepLast.add(
                Promise.all(tasks.map((task) => task.prom)),
            );
        } catch (error) {
            if (error instanceof SupersededError) {
                return;
            }
            throw error;
        }
        tasks.forEach((task, index) => {
            subItems[task.id] = taskResults[index];
        });

        this.state.expanded = expanded;
        this.state.query = query;
        this.subItems = subItems;

        if (this.inputRef.el) {
            /** @type {HTMLInputElement} */ (this.inputRef.el).value = query;
        }

        const trimmedQuery = this.state.query.trim();

        this.items.length = 0;
        if (!trimmedQuery) {
            return;
        }

        for (const searchItem of this.searchItemsFields) {
            this.items.push(...this.getItems(searchItem, trimmedQuery));
        }

        this.items.push({
            id: nextItemId++,
            title: _t("Add a custom filter"),
            isAddCustomFilterButton: true,
        });
    }

    /**
     * @param {Object} searchItem
     * @param {string} fieldType
     * @param {boolean} isFieldProperty
     * @returns {string|null}
     */
    getRowPreposition(searchItem, fieldType, isFieldProperty) {
        if (
            (isFieldProperty && FOLDABLE_TYPES.includes(fieldType)) ||
            fieldType === "properties"
        ) {
            return null;
        }
        return this.getPreposition(searchItem);
    }

    /**
     * @param {Object} searchItem
     * @param {string} trimmedQuery
     * @param {Object} rowBase
     * @returns {Object[]}
     */
    getEnumeratedItems(searchItem, trimmedQuery, rowBase) {
        const booleanOptions = [
            [true, _t("Yes")],
            [false, _t("No")],
        ];
        let options = booleanOptions;
        if (searchItem.type === "field_property") {
            const { selection, tags } = searchItem.propertyFieldDefinition || {};
            options = selection || tags || booleanOptions;
        }
        const items = [];
        for (const [value, label] of options) {
            if (fuzzyTest(trimmedQuery.toLowerCase(), label.toLowerCase())) {
                items.push({
                    ...rowBase,
                    id: nextItemId++,
                    label,
                    operator: searchItem.operator || "=",
                    value,
                });
            }
        }
        return items;
    }

    /**
     * @param {Object} item
     * @param {string} fieldType
     * @param {Object} searchItem
     */
    markFoldable(item, fieldType, searchItem) {
        if (searchItem.type === "field_property") {
            item.isParent = FOLDABLE_TYPES.includes(fieldType);
            item.unselectable = item.isParent;
            item.propertyItemId = searchItem.propertyItemId;
        } else if (fieldType === "properties") {
            item.isParent = true;
            item.unselectable = true;
        } else if (fieldType === "many2one" || fieldType === "selection") {
            item.isParent = true;
        }
        if (item.isParent) {
            item.isExpanded = this.state.expanded.includes(item.searchItemId);
        }
    }

    /**
     * @param {Object} searchItem
     * @param {string} trimmedQuery
     * @returns {Object[]}
     */
    getItems(searchItem, trimmedQuery) {
        const isFieldProperty = searchItem.type === "field_property";
        const fieldType = this.getFieldType(searchItem);
        const rowBase = {
            fieldType,
            searchItemDescription: searchItem.description,
            preposition: this.getRowPreposition(searchItem, fieldType, isFieldProperty),
            searchItemId: searchItem.id,
            isFieldProperty,
        };

        if (
            ["boolean", "tags"].includes(fieldType) ||
            (isFieldProperty && fieldType === "selection")
        ) {
            return this.getEnumeratedItems(searchItem, trimmedQuery, rowBase);
        }

        let value;
        try {
            value = parseValue(trimmedQuery, fieldType);
        } catch {
            return [];
        }

        /** @type {Record<string, any>} */
        const item = {
            ...rowBase,
            id: nextItemId++,
            label: this.state.query,
            operator:
                searchItem.operator ||
                (CHAR_FIELDS.includes(fieldType) ? "ilike" : "="),
            value,
        };
        this.markFoldable(item, fieldType, searchItem);

        const items = [item];
        if (item.isExpanded) {
            const subItems = this.subItems[searchItem.id] || [];
            if (searchItem.type === "field" && searchItem.fieldType === "properties") {
                for (const subItem of subItems) {
                    items.push(...this.getItems(subItem, trimmedQuery));
                }
            } else {
                items.push(...subItems);
            }
        }
        return items;
    }

    getPreposition(searchItem) {
        const fieldType = this.getFieldType(searchItem);
        return ["date", "datetime"].includes(fieldType) ? _t("at") : _t("for");
    }

    getFieldType(searchItem) {
        const { type } =
            (searchItem.type === "field_property"
                ? searchItem.propertyFieldDefinition
                : this.fields[searchItem.fieldName]) || {};
        return type === "reference" ? "char" : type;
    }

    /**
     * @param {Object} searchItem
     * @param {string} query
     * @returns {Promise<Object[]>}
     */
    _getSubItems(searchItem, query) {
        const key = `${searchItem.id}|${query}|${this.state.subItemsLimits[searchItem.id]}`;
        let prom = this._pendingSubItems.get(key);
        if (!prom) {
            prom = this.computeSubItems(searchItem, query);
            this._pendingSubItems.set(key, prom);
            const forget = () => {
                if (this._pendingSubItems.get(key) === prom) {
                    this._pendingSubItems.delete(key);
                }
            };
            // not .finally(): its derived promise would reject a second time
            prom.then(forget, forget);
        }
        return prom;
    }

    /**
     * @param {Object} searchItem
     * @param {string} label
     * @returns {Object}
     */
    makeSubItemNotice(searchItem, label) {
        return {
            id: nextItemId++,
            isChild: true,
            searchItemId: searchItem.id,
            label,
            unselectable: true,
        };
    }

    /**
     * @param {Object} searchItem
     * @param {Object} field
     * @param {string} query
     * @returns {Promise<{options: any[][], showLoadMore: boolean, failed?: boolean}>}
     */
    async fetchRelationalOptions(searchItem, field, query) {
        let domain = [];
        if (searchItem.domain) {
            const domainEvalContext = {
                ...this.env.searchModel.domainEvalContext,
                ...field.context,
            };
            domain = new Domain(searchItem.domain).toList(domainEvalContext);
        }
        const relation =
            searchItem.type === "field_property"
                ? searchItem.propertyFieldDefinition.comodel
                : field.relation;

        const limitToFetch = this.state.subItemsLimits[searchItem.id] + 1;
        let options;
        try {
            options = await this.orm.call(relation, "name_search", [], {
                domain: domain,
                context: {
                    ...this.env.searchModel.globalContext,
                    ...field.context,
                },
                limit: limitToFetch,
                name: query.trim(),
            });
        } catch {
            return { options: [], showLoadMore: false, failed: true };
        }
        if (options.length === limitToFetch) {
            options.pop();
            return { options, showLoadMore: true };
        }
        return { options, showLoadMore: false };
    }

    /**
     * @param {Object} searchItem
     * @param {string} query
     * @returns {Promise<Object[]>}
     */
    async computeSubItems(searchItem, query) {
        const field = this.fields[searchItem.fieldName];
        let options;
        let showLoadMore = false;
        if (searchItem.fieldType === "selection") {
            options = field.selection.filter(([_, label]) =>
                fuzzyTest(query.toLowerCase(), label.toLowerCase()),
            );
        } else {
            const fetched = await this.fetchRelationalOptions(searchItem, field, query);
            if (fetched.failed) {
                return [this.makeSubItemNotice(searchItem, _t("(loading failed)"))];
            }
            ({ options, showLoadMore } = fetched);
        }

        const subItems = [];
        if (options.length) {
            const operator = searchItem.operator || "=";
            for (const [value, label] of options) {
                subItems.push({
                    id: nextItemId++,
                    isChild: true,
                    searchItemId: searchItem.id,
                    value,
                    label,
                    operator,
                });
            }
            if (showLoadMore) {
                subItems.push({
                    ...this.makeSubItemNotice(searchItem, _t("Load more")),
                    loadMore: () => {
                        this.state.subItemsLimits[searchItem.id] +=
                            SUB_ITEMS_DEFAULT_LIMIT;
                        const newSubItems = { ...this.subItems };
                        newSubItems[searchItem.id] = undefined;
                        this.computeState({ subItems: newSubItems });
                    },
                });
            }
        } else {
            subItems.push(this.makeSubItemNotice(searchItem, _t("(no result)")));
        }
        return subItems;
    }

    /** @param {Object} facet */
    removeFacet(facet) {
        this.env.searchModel.deactivateGroup(facet.groupId);
        this.inputRef.el?.focus();
    }

    resetState(options = { focus: true }) {
        this.state.subItemsLimits = {};
        this.computeState({ expanded: [], query: "", subItems: {} });
        if (options.focus) {
            this.inputRef.el?.focus();
        }
    }

    /** @param {Object} item */
    selectItem(item) {
        if (item.isAddCustomFilterButton) {
            return this.env.searchModel.spawnCustomFilterDialog();
        }

        const searchItem = this.getSearchItem(item.searchItemId);
        if (
            (searchItem.fieldType === "selection" && !item.isChild) ||
            (searchItem.type === "field" && searchItem.fieldType === "properties") ||
            (searchItem.type === "field_property" && item.unselectable)
        ) {
            this.toggleItem(item, !item.isExpanded);
            return;
        }

        if (!item.unselectable) {
            const { searchItemId, fieldType, operator } = item;
            let { label, value } = item;
            if (
                !["selection", "boolean", "tags"].includes(fieldType) &&
                this.state.query !== label &&
                !item.isChild
            ) {
                try {
                    value = parseValue(this.state.query.trim(), fieldType);
                    label = this.state.query;
                } catch {}
            }
            this.env.searchModel.addAutoCompletionValues(searchItemId, {
                label,
                operator,
                value,
            });
        }

        if (item.loadMore) {
            item.loadMore();
        } else {
            this.inputDropdownState.close();
            this.resetState();
        }
    }

    /**
     * @param {Object} item
     * @param {boolean} shouldExpand
     */
    toggleItem(item, shouldExpand) {
        const id = item.searchItemId;
        const expanded = [...this.state.expanded];
        const index = expanded.findIndex((id0) => id0 === id);
        if (shouldExpand === true) {
            if (index < 0) {
                expanded.push(id);
            }
        } else {
            if (index >= 0) {
                expanded.splice(index, 1);
            }
        }
        this.computeState({ expanded });
    }

    setupFacetNavigation() {
        const isFacet = (target) => target?.classList.contains("o_searchview_facet");

        useNavigation(this.facetContainerRef, {
            shouldFocusChildInput: false,
            getItems: () => {
                if (this.root.el && this.inputRef.el) {
                    return [
                        ...this.root.el.querySelectorAll(":scope .o_searchview_facet"),
                        this.inputRef.el,
                    ];
                }
                return [];
            },
            hotkeys: {
                tab: {
                    isAvailable: () => false,
                },
                "shift+tab": {
                    isAvailable: () => false,
                },
                enter: {
                    isAvailable: () => !this.inputDropdownState.isOpen,
                    callback: () => this.env.searchModel.search(),
                },
                arrowdown: {
                    callback: () =>
                        this.env.searchModel.trigger(SearchModelEvent.FOCUS_VIEW),
                },
                backspace: {
                    bypassEditableProtection: true,
                    allowRepeat: false,
                    isAvailable: ({ target }) =>
                        isFacet(target) ||
                        (target.selectionStart === 0 && target.selectionEnd === 0),
                    callback: (navigator) => {
                        const facets = this.env.searchModel.facets;
                        if (isFacet(navigator.activeItem.el)) {
                            this.removeFacet(facets[navigator.activeItemIndex]);
                        } else if (facets.length) {
                            this.removeFacet(facets.at(-1));
                        }
                    },
                },
                arrowright: {
                    bypassEditableProtection: true,
                    allowRepeat: false,
                    isAvailable: ({ target }) =>
                        isFacet(target) ||
                        target.selectionStart === this.state.query.length,
                    callback: (navigator) => {
                        navigator.next();
                        if (navigator.activeItem.el === this.inputRef.el) {
                            /** @type {HTMLInputElement} */ (
                                this.inputRef.el
                            ).setSelectionRange(0, 0);
                        }
                    },
                },
                arrowleft: {
                    bypassEditableProtection: true,
                    isAvailable: ({ target }) =>
                        isFacet(target) || target.selectionStart === 0,
                    callback: (navigator) => {
                        navigator.previous();
                        if (navigator.activeItem.el === this.inputRef.el) {
                            const input = /** @type {HTMLInputElement} */ (
                                this.inputRef.el
                            );
                            const inputLength = input.value.length;
                            input.setSelectionRange(inputLength, inputLength);
                        }
                    },
                },
            },
        });
    }

    /** @returns {import("@web/core/navigation/navigation").NavigationOptions} */
    getDropdownNavigation() {
        const isExpansible = (index) => {
            const item = this.items[index];
            return item?.isParent;
        };

        const isCollapsible = (index) => {
            const item = this.items[index];
            return (
                item &&
                ((item.isParent && item.isExpanded) ||
                    item.isChild ||
                    item.isFieldProperty)
            );
        };

        return {
            virtualFocus: true,
            getItems: () =>
                /** @type {any} */ (this.menuRef).el?.querySelectorAll(
                    ":scope .o-dropdown-item",
                ) ?? [],
            isNavigationAvailable: ({ navigator, target }) =>
                this.inputDropdownState.isOpen &&
                (this.facetContainerRef.el?.contains(target) ||
                    navigator.contains(target)),
            onUpdated: (navigator) => (this.navigator = navigator),
            onItemActivated: (itemEl) =>
                (this.lastActiveItemId = Number.parseInt(itemEl.id, 10)),
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
                    isAvailable: ({ navigator }) =>
                        isExpansible(navigator.activeItemIndex),
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
                    isAvailable: ({ navigator }) =>
                        isCollapsible(navigator.activeItemIndex),
                    callback: (navigator) => {
                        const item = this.items[navigator.activeItemIndex];

                        const findIndex = (id) =>
                            this.items.findIndex(
                                (item) => item.isParent && item.searchItemId === id,
                            );
                        if (item.isParent && item.isExpanded) {
                            this.toggleItem(item, false);
                        } else if (item.isChild) {
                            navigator.items[findIndex(item.searchItemId)]?.setActive();
                        } else {
                            navigator.items[
                                findIndex(item.propertyItemId)
                            ]?.setActive();
                        }
                    },
                },
            },
        };
    }

    /**
     * @param {Object} facet
     * @returns {string}
     */
    getFacetName(facet) {
        const values = facet.values.join(` ${facet.separator} `);
        return facet.title ? `${facet.title}: ${values}` : values;
    }

    /**
     * @param {Object} facet
     * @returns {string}
     */
    getFacetRemoveLabel(facet) {
        return _t("Remove %s", this.getFacetName(facet));
    }

    /**
     * @param {Object} facet
     * @returns {boolean}
     */
    isFacetLabelClickable(facet) {
        return Boolean(
            (this.env.searchModel.canOrderByCount && facet.type === "groupBy") ||
            facet.domain,
        );
    }

    onFacetLabelClick(facet) {
        const { domain, groupId } = facet;
        if (this.env.searchModel.canOrderByCount && facet.type === "groupBy") {
            this.env.searchModel.switchGroupBySort();
        } else if (domain) {
            this.env.searchModel.spawnCustomFilterDialog({ domain, groupId });
        }
    }

    /** @param {Object} facet */
    onFacetRemove(facet) {
        this.removeFacet(facet);
    }

    onSearchClick() {
        if (!hasTouch()) {
            if (!(/** @type {HTMLInputElement} */ (this.inputRef.el).value.length)) {
                this.searchBarDropdownState.open();
            } else {
                this.inputDropdownState.open();
            }
        }
    }

    /** @param {InputEvent} ev */
    onSearchInput(ev) {
        if (!hasTouch()) {
            this.searchBarDropdownState.close();
        }
        const query = /** @type {HTMLInputElement} */ (ev.target).value;
        if (query.trim()) {
            if (!ev.isComposing) {
                this.inputDropdownState.open();
            }
            this.state.subItemsLimits = {};
            this.computeState({ query, expanded: [], subItems: {} });
        } else {
            this.inputDropdownState.close();
            this.resetState();
        }
    }

    /** @param {CompositionEvent} ev */
    onCompositionEnd(ev) {
        const query = /** @type {HTMLInputElement} */ (ev.target).value;
        if (query.trim()) {
            this.inputDropdownState.open();
        }
    }

    onClickSearchIcon() {
        if (!this.state.query.length) {
            this.env.searchModel.search();
        } else {
            const item = this.items.find((item) => item.id === this.lastActiveItemId);
            if (item) {
                this.selectItem(item);
            }
        }
    }

    onInputDropdownChanged(isOpen) {
        if (isOpen !== this.inputDropdownState.isOpen) {
            log.logic("dropdown-state-stale", () => ({
                isOpen,
                current: this.inputDropdownState.isOpen,
            }));
            return;
        }
        if (!isOpen && status(this) === "mounted") {
            this.resetState({ focus: false });
        } else if (this.navigator) {
            this.navigator.items[0]?.setActive();
        }
    }
}
