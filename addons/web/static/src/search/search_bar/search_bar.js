import { Domain } from "@web/core/domain";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { KeepLast } from "@web/core/utils/concurrency";
import { useAutofocus, useBus, useChildRef, useService } from "@web/core/utils/hooks";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { fuzzyTest } from "@web/core/utils/search";
import { _t } from "@web/core/l10n/translation";
import { SearchBarMenu } from "../search_bar_menu/search_bar_menu";
import { Component, status, useRef, useState } from "@odoo/owl";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { hasTouch } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ACTIVE_ELEMENT_CLASS, useNavigation } from "@web/core/navigation/navigation";

const parsers = registry.category("parsers");

const CHAR_FIELDS = ["char", "html", "many2many", "many2one", "one2many", "text", "properties"];
const FOLDABLE_TYPES = ["properties", "many2one", "many2many"];

let nextItemId = 1;
const SUB_ITEMS_DEFAULT_LIMIT = 8;

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

    setup() {
        this.dialogService = useService("dialog");
        this.fields = this.env.searchModel.searchViewFields;
        this.searchItemsFields = this.env.searchModel.getSearchItems((f) => f.type === "field");
        this.root = useRef("root");
        this.ui = useService("ui");

        this.visibilityState = useState(this.props.toggler?.state || { showSearchBar: true });

        // core state
        this.state = useState({
            expanded: [],
            query: "",
            subItemsLimits: {},
        });

        // derived state
        this.items = useState([]);
        this.subItems = {};

        this.facetContainerRef = useRef("facetContainerRef");
        this.menuRef = useChildRef();
        this.setupFacetNavigation();
        this.inputDropdownState = useDropdownState();
        this.inputDropdownNavOptions = this.getDropdownNavigation();

        this.searchBarDropdownState = useDropdownState();

        this.orm = useService("orm");

        this.keepLast = new KeepLast();

        this.inputRef =
            this.env.config.disableSearchBarAutofocus || !this.props.autofocus
                ? useRef("autofocus")
                : useAutofocus({ mobile: this.props.toggler !== undefined }); // only force the focus on touch devices when the toggler is present on small devices

        useBus(this.env.searchModel, "focus-search", () => {
            this.inputRef.el.focus();
        });

        useBus(this.env.searchModel, "update", this.render);
    }

    /**
     * @param {number} id
     * @param {Object}
     */
    getSearchItem(id) {
        return this.env.searchModel.searchItems[id];
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
            const searchItem = this.getSearchItem(id);
            if (searchItem.type === "field" && searchItem.fieldType === "properties") {
                tasks.push({ id, prom: this.getSearchItemsProperties(searchItem) });
            } else if (!subItems[id]) {
                if (!this.state.subItemsLimits[id]) {
                    this.state.subItemsLimits[id] = SUB_ITEMS_DEFAULT_LIMIT;
                }
                tasks.push({ id, prom: this.computeSubItems(searchItem, query) });
            }
        }

        const prom = this.keepLast.add(Promise.all(tasks.map((task) => task.prom)));

        if (tasks.length) {
            const taskResults = await prom;
            tasks.forEach((task, index) => {
                subItems[task.id] = taskResults[index];
            });
        }

        this.state.expanded = expanded;
        this.state.query = query;
        this.subItems = subItems;

        this.inputRef.el.value = query;

        const trimmedQuery = this.state.query.trim();

        this.items.length = 0;
        if (!trimmedQuery) {
            return;
        }

        for (const searchItem of this.searchItemsFields) {
            this.items.push(...this.getItems(searchItem, trimmedQuery));
        }

        this.items.push({
            title: _t("Add a custom filter"),
            isAddCustomFilterButton: true,
        });
    }

    /**
     * @param {Object} searchItem
     * @param {string} trimmedQuery
     * @returns {Object[]}
     */
    getItems(searchItem, trimmedQuery) {
        const items = [];

        const isFieldProperty = searchItem.type === "field_property";
        const fieldType = this.getFieldType(searchItem);

        /** @todo do something with respect to localization (rtl) */
        let preposition = this.getPreposition(searchItem);

        if ((isFieldProperty && FOLDABLE_TYPES.includes(fieldType)) || fieldType === "properties") {
            // Do not chose preposition for foldable properties
            // or the properties item itself
            preposition = null;
        }
        if (
            ["boolean", "tags"].includes(fieldType) ||
            (isFieldProperty && fieldType === "selection")
        ) {
            const booleanOptions = [
                [true, _t("Yes")],
                [false, _t("No")],
            ];
            let options;
            if (isFieldProperty) {
                const { selection, tags } = searchItem.propertyFieldDefinition || {};
                options = selection || tags || booleanOptions;
            } else {
                options = booleanOptions;
            }
            for (const [value, label] of options) {
                if (fuzzyTest(trimmedQuery.toLowerCase(), label.toLowerCase())) {
                    items.push({
                        id: nextItemId++,
                        searchItemDescription: searchItem.description,
                        preposition,
                        searchItemId: searchItem.id,
                        label,
                        /** @todo check if searchItem.operator is fine (here and elsewhere) */
                        operator: searchItem.operator || "=",
                        value,
                        isFieldProperty,
                    });
                }
            }
            return items;
        }

        const parser = parsers.contains(fieldType) ? parsers.get(fieldType) : (str) => str;
        let value;
        try {
            switch (fieldType) {
                case "date":
                    value = serializeDate(parser(trimmedQuery));
                    break;
                case "datetime":
                    value = serializeDateTime(parser(trimmedQuery));
                    break;
                case "selection":
                case "many2one":
                    value = trimmedQuery;
                    break;
                default:
                    value = parser(trimmedQuery);
            }
        } catch {
            return [];
        }

        const item = {
            id: nextItemId++,
            searchItemDescription: searchItem.description,
            preposition,
            searchItemId: searchItem.id,
            label: this.state.query,
            operator: searchItem.operator || (CHAR_FIELDS.includes(fieldType) ? "ilike" : "="),
            value,
            isFieldProperty,
        };

        if (isFieldProperty) {
            item.isParent = FOLDABLE_TYPES.includes(fieldType);
            item.unselectable = FOLDABLE_TYPES.includes(fieldType);
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

        items.push(item);

        if (item.isExpanded) {
            if (searchItem.type === "field" && searchItem.fieldType === "properties") {
                for (const subItem of this.subItems[searchItem.id]) {
                    items.push(...this.getItems(subItem, trimmedQuery));
                }
            } else {
                items.push(...this.subItems[searchItem.id]);
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
            searchItem.type === "field_property"
                ? searchItem.propertyFieldDefinition
                : this.fields[searchItem.fieldName];
        const fieldType = type === "reference" ? "char" : type;

        return fieldType;
    }

    /**
     * @param {Object} searchItem
     * @returns {Object[]}
     */
    getSearchItemsProperties(searchItem) {
        return this.env.searchModel.getSearchItemsProperties(searchItem);
    }

    /**
     * @param {Object} searchItem
     * @param {string} query
     * @returns {Object[]}
     */
    async computeSubItems(searchItem, query) {
        const field = this.fields[searchItem.fieldName];
        let options = [];
        let showLoadMore = false;
        if (searchItem.fieldType === "selection") {
            options = field.selection.filter(([_, label]) =>
                fuzzyTest(query.toLowerCase(), label.toLowerCase())
            );
        } else {
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
            options = await this.orm.call(relation, "name_search", [], {
                domain: domain,
                context: { ...this.env.searchModel.globalContext, ...field.context },
                limit: limitToFetch,
                name: query.trim(),
            });

            if (options.length === limitToFetch) {
                options.pop();
                showLoadMore = true;
            }
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
                    id: nextItemId++,
                    isChild: true,
                    searchItemId: searchItem.id,
                    label: _t("Load more"),
                    unselectable: true,
                    loadMore: () => {
                        this.state.subItemsLimits[searchItem.id] += SUB_ITEMS_DEFAULT_LIMIT;
                        const newSubItems = [...this.subItems];
                        newSubItems[searchItem.id] = undefined;
                        this.computeState({ subItems: newSubItems });
                    },
                });
            }
        } else {
            subItems.push({
                id: nextItemId++,
                isChild: true,
                searchItemId: searchItem.id,
                label: _t("(no result)"),
                unselectable: true,
            });
        }
        return subItems;
    }

    /**
     * @param {number} [index]
     */
    focusFacet(index) {
        const facets = this.root.el.getElementsByClassName("o_searchview_facet");
        if (facets.length) {
            if (index === undefined) {
                facets[facets.length - 1].focus();
            } else {
                facets[index].focus();
            }
        }
    }

    /**
     * @param {Object} facet
     */
    removeFacet(facet) {
        this.env.searchModel.deactivateGroup(facet.groupId);
        this.inputRef.el.focus();
    }

    resetState(options = { focus: true }) {
        this.state.subItemsLimits = {};
        this.computeState({ expanded: [], query: "", subItems: [] });
        if (options.focus) {
            this.inputRef.el.focus();
        }
    }

    /**
     * @param {Object} item
     */
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
            const { searchItemId, label, operator, value } = item;
            this.env.searchModel.addAutoCompletionValues(searchItemId, { label, operator, value });
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
        const isFacet = (target) => target && target.classList.contains("o_searchview_facet");

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
            isNavigationAvailable: ({ navigator, target }) => navigator.contains(target),
            hotkeys: {
                enter: {
                    isAvailable: () => !this.inputDropdownState.isOpen,
                    callback: () => this.env.searchModel.search() /** @todo keep this thing ?*/,
                },
                arrowdown: {
                    callback: () => this.env.searchModel.trigger("focus-view"),
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
                        } else if (facets.length > 0) {
                            this.removeFacet(facets[facets.length - 1]);
                        }
                    },
                },
                arrowright: {
                    bypassEditableProtection: true,
                    allowRepeat: false,
                    isAvailable: ({ target }) =>
                        isFacet(target) || target.selectionStart === this.state.query.length,
                    callback: (navigator) => {
                        navigator.next();
                        if (navigator.activeItem.el === this.inputRef.el) {
                            this.inputRef.el.setSelectionRange(0, 0);
                        }
                    },
                },
                arrowleft: {
                    bypassEditableProtection: true,
                    isAvailable: ({ target }) => isFacet(target) || target.selectionStart === 0,
                    callback: (navigator) => {
                        navigator.previous();
                        if (navigator.activeItem.el === this.inputRef.el) {
                            const inputLength = this.inputRef.el.value.length;
                            this.inputRef.el.setSelectionRange(inputLength, inputLength);
                        }
                    },
                },
            },
        });
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
            return (
                item && ((item.isParent && item.isExpanded) || item.isChild || item.isFieldProperty)
            );
        };

        return {
            virtualFocus: true,
            getItems: () => this.menuRef.el?.querySelectorAll(":scope .o-dropdown-item") ?? [],
            isNavigationAvailable: ({ navigator, target }) =>
                this.inputDropdownState.isOpen &&
                (this.facetContainerRef.el?.contains(target) || navigator.contains(target)),
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
                                (item) => item.isParent && item.searchItemId === id
                            );
                        if (item && item.isParent && item.isExpanded) {
                            this.toggleItem(item, false);
                        } else if (item && item.isChild) {
                            navigator.items[findIndex(item.searchItemId)]?.setActive();
                        } else if (item && item.isFieldProperty) {
                            navigator.items[findIndex(item.propertyItemId)]?.setActive();
                        } else if (this.inputRef.el.selectionStart === 0) {
                            navigator.items[this.env.searchModel.facets.length - 1]?.setActive();
                        }
                    },
                },
            },
        };
    }

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    onFacetLabelClick(target, facet) {
        const { domain, groupId } = facet;
        if (this.env.searchModel.canOrderByCount && facet.type === "groupBy") {
            this.env.searchModel.switchGroupBySort();
            return;
        } else if (!domain) {
            return;
        }
        const { resModel } = this.env.searchModel;
        this.dialogService.add(DomainSelectorDialog, {
            resModel,
            domain,
            context: this.env.searchModel.domainEvalContext,
            onConfirm: (nextDomain) => {
                if (nextDomain !== domain) {
                    this.env.searchModel.splitAndAddDomain(nextDomain, groupId);
                }
            },
            disableConfirmButton: (domain) => domain === `[]`,
            title: _t("Custom Filter"),
            confirmButtonText: _t("Search"),
            discardButtonText: _t("Discard"),
            isDebugMode: this.env.searchModel.isDebugMode,
        });
    }

    /**
     * @param {Object} facet
     */
    onFacetRemove(facet) {
        this.removeFacet(facet);
    }

    onSearchClick() {
        if (!hasTouch()) {
            if (!this.inputRef.el.value.length) {
                this.searchBarDropdownState.open();
            } else {
                this.inputDropdownState.open();
            }
        }
    }

    /**
     * @param {InputEvent} ev
     */
    onSearchInput(ev) {
        if (!hasTouch()) {
            this.searchBarDropdownState.close();
        }
        const query = ev.target.value;
        if (query.trim()) {
            if (!ev.isComposing) {
                // Protection for IME input
                this.inputDropdownState.open();
            }
            this.computeState({ query, expanded: [], subItems: [] });
        } else if (this.items.length) {
            this.inputDropdownState.close();
            this.resetState();
        }
    }
    
    /**
     * @param {CompositionEvent} ev
     */
    onCompositionEnd(ev) {
        const query = ev.target.value;
        if (query.trim()) {
            // Open dropdown after IME composition is complete
            this.inputDropdownState.open();
        }
    }

    onClickSearchIcon() {
        if (!this.state.query.length) {
            this.env.searchModel.search();
        } else {
            const els = [
                ...this.root.el.ownerDocument.querySelectorAll(
                    ".o_searchview_autocomplete .o-dropdown-item"
                ),
            ];
            const index = els.findIndex((el) => el.classList.contains(ACTIVE_ELEMENT_CLASS));
            if (this.items[index]) {
                this.selectItem(this.items[index]);
            }
        }
    }

    onToggleSearchBar() {
        this.state.showSearchBar = !this.state.showSearchBar;
    }

    onInputDropdownChanged(isOpen) {
        if (!isOpen && status(this) === "mounted") {
            this.resetState({ focus: false });
        } else if (this.navigator) {
            this.navigator.items[0]?.setActive();
        }
    }
}
