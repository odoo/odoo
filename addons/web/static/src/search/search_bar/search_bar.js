/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { KeepLast } from "@web/core/utils/concurrency";
import { useAutofocus, useBus, useService } from "@web/core/utils/hooks";
import { fuzzyTest } from "@web/core/utils/search";

import { Component, useExternalListener, useRef, useState } from "@odoo/owl";
const parsers = registry.category("parsers");

const CHAR_FIELDS = ["char", "html", "many2many", "many2one", "one2many", "text", "properties"];
const FOLDABLE_TYPES = ["properties", "many2one", "many2many"];

let nextItemId = 1;

export class SearchBar extends Component {
    setup() {
        this.fields = this.env.searchModel.searchViewFields;
        this.searchItems = this.env.searchModel.getSearchItems((f) => ["field", "field_property"].includes(f.type));
        this.root = useRef("root");

        // core state
        this.state = useState({
            expanded: [],
            focusedIndex: 0,
            query: "",
        });

        // derived state
        this.items = useState([]);
        this.subItems = {};

        this.orm = useService("orm");

        this.keepLast = new KeepLast();

        this.inputRef = this.env.config.disableSearchBarAutofocus
            ? useRef("autofocus")
            : useAutofocus();

        useBus(this.env.searchModel, "focus-search", () => {
            this.inputRef.el.focus();
        });

        useBus(this.env.searchModel, "update", this.render);

        useExternalListener(window, "click", this.onWindowClick);
        useExternalListener(window, "keydown", this.onWindowKeydown);
    }

    //---------------------------------------------------------------------
    // Private
    //---------------------------------------------------------------------

    /**
     * @param {Object} [options={}]
     * @param {number[]} [options.expanded]
     * @param {number} [options.focusedIndex]
     * @param {string} [options.query]
     * @param {Object[]} [options.subItems]
     * @returns {Object[]}
     */
    async computeState(options = {}) {
        const query = "query" in options ? options.query : this.state.query;
        const expanded = "expanded" in options ? options.expanded : this.state.expanded;
        const focusedIndex =
            "focusedIndex" in options ? options.focusedIndex : this.state.focusedIndex;
        const subItems = "subItems" in options ? options.subItems : this.subItems;

        const tasks = [];
        const expandedSearchItems = this.searchItems.filter((item) => expanded.includes(item.id));
        for (const searchItem of expandedSearchItems) {
            // expand a properties should lazily fetch the definition, and generate
            // searchItems, so the normal field logic is used for properties
            const field = this.fields[searchItem.fieldName];

            if (field.type === "properties" && searchItem.type === "field") {
                tasks.push({ id: searchItem.id, prom: this.insertPropertiesSearchItems(searchItem, field, query) });
            } else if (!subItems[searchItem.id]) {
                tasks.push({ id: searchItem.id, prom: this.computeSubItems(searchItem, query) });
            }
        }

        const prom = this.keepLast.add(Promise.all(tasks.map((task) => task.prom)));

        if (tasks.length) {
            const taskResults = await prom;
            tasks.forEach((task, index) => {
                subItems[task.id] = taskResults[index] || [];
            });
        }

        this.state.expanded = expanded;
        this.state.query = query;
        this.state.focusedIndex = focusedIndex;
        this.subItems = subItems;

        this.inputRef.el.value = query;

        const trimmedQuery = this.state.query.trim();

        this.items.length = 0;
        if (!trimmedQuery) {
            return;
        }

        // move properties under their related field
        const searchItems = [...this.searchItems];
        searchItems.sort((a, b) => (a.propertyItemId || a.id) - (b.propertyItemId || b.id));

        for (const searchItem of searchItems) {
            const field = this.fields[searchItem.fieldName];
            const isPropertyFieldAttribute = field.type === "properties" && searchItem.type === "field_property";
            let fieldType = field.type === "reference" ? "char" : field.type;

            if (isPropertyFieldAttribute) {
                // take the definition type instead
                if (!this.state.expanded.includes(searchItem.propertyItemId)) {
                    // properties field not unfolded, do not show the option
                    continue;
                }
                fieldType = searchItem.propertyFieldDefinition.type;
            }

            /** @todo do something with respect to localization (rtl) */
            let preposition = this.env._t(["date", "datetime"].includes(fieldType) ? "at" : "for");

            if (fieldType === "properties" || (isPropertyFieldAttribute && FOLDABLE_TYPES.includes(fieldType))) {
                // Do not chose preposition for foldable properties
                // or the properties item itself
                preposition = null;
            }

            if (["selection", "boolean", "tags"].includes(fieldType)) {
                const propertyDefinition = searchItem.propertyFieldDefinition || {};
                const options = propertyDefinition.selection
                    || propertyDefinition.tags
                    || field.selection
                    || [[true, this.env._t("Yes")], [false, this.env._t("No")]];

                for (const [value, label] of options) {
                    if (fuzzyTest(trimmedQuery.toLowerCase(), label.toLowerCase())) {
                        this.items.push({
                            id: nextItemId++,
                            searchItemDescription: searchItem.description,
                            preposition,
                            searchItemId: searchItem.id,
                            label,
                            /** @todo check if searchItem.operator is fine (here and elsewhere) */
                            operator: searchItem.operator || "=",
                            value,
                            isPropertyFieldAttribute,
                        });
                    }
                }
                continue;
            }

            const parser = parsers.contains(fieldType) ? parsers.get(fieldType) : (str) => str;
            let value;
            try {
                switch (fieldType) {
                    case "date": {
                        value = serializeDate(parser(trimmedQuery));
                        break;
                    }
                    case "datetime": {
                        value = serializeDateTime(parser(trimmedQuery));
                        break;
                    }
                    case "many2one": {
                        value = trimmedQuery;
                        break;
                    }
                    default: {
                        value = parser(trimmedQuery);
                    }
                }
            } catch {
                continue;
            }

            const item = {
                id: nextItemId++,
                searchItemDescription: searchItem.description,
                preposition,
                searchItemId: searchItem.id,
                label: this.state.query,
                operator: searchItem.operator || (CHAR_FIELDS.includes(fieldType) ? "ilike" : "="),
                value,
                isPropertyFieldAttribute,
            };

            if (fieldType === "properties" || isPropertyFieldAttribute) {
                item.isParent = !isPropertyFieldAttribute || FOLDABLE_TYPES.includes(fieldType);
                item.unselectable = (
                    !isPropertyFieldAttribute
                    || FOLDABLE_TYPES.includes(fieldType)
                    || searchItem.propertyType === "many2one"
                );
                item.isExpanded = this.state.expanded.includes(item.searchItemId);
            } else if (fieldType === "many2one") {
                item.isParent = true;
                item.isExpanded = this.state.expanded.includes(item.searchItemId);
            }

            this.items.push(item);

            if (item.isExpanded) {
                this.items.push(...this.subItems[searchItem.id]);
            }
        }
    }

    /**
     * @param {number} searchItemId
     * @param {string} query
     * @returns {Object[]}
     */
    async computeSubItems(searchItem, query) {
        const field = this.fields[searchItem.fieldName];
        let domain = [];
        if (searchItem.domain) {
            try {
                domain = new Domain(searchItem.domain).toList();
            } catch {
                // Pass
            }
        }
        const relation = field.relation || searchItem.propertyFieldDefinition.comodel;

        const options = await this.orm.call(relation, "name_search", [], {
            args: domain,
            context: { ...this.env.searchModel.globalContext, ...field.context },
            limit: 8,
            name: query.trim(),
        });
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
        } else {
            subItems.push({
                id: nextItemId++,
                isChild: true,
                searchItemId: searchItem.id,
                label: this.env._t("(no result)"),
                unselectable: true,
            });
        }
        return subItems;
    }

    /**
     * Insert the properties items, only when we unfold the properties field
     * (will fetch the properties definition on the parent to generate the items).
     *
     * Because it require a RPC call to get the properties search items,
     * it's done lazily, only when we need them.
     *
     * @param {Object} searchItem
     * @param {Object} field
     */
    async insertPropertiesSearchItems(searchItem, field) {
        const definitionRecord = field.definition_record;
        const definitionRecordModel = this.fields[definitionRecord].relation;
        const definitionRecordField = field.definition_record_field;

        const propertiesSearchItems = await this.env.searchModel.getSearchItemsProperty(
            searchItem, definitionRecord, definitionRecordModel, definitionRecordField);

        const searchItems = this.searchItems.filter(
            item => item.propertyItemId !== searchItem.id);

        this.searchItems = [...searchItems, ...propertiesSearchItems];
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

    resetState() {
        this.computeState({ expanded: [], focusedIndex: 0, query: "", subItems: [] });
        this.inputRef.el.focus();
    }

    /**
     * @param {Object} item
     */
    selectItem(item) {
        const searchItem = this.searchItems.find(searchItem => searchItem.id === item.searchItemId);
        if((searchItem.fieldType === "properties" && searchItem.type === "field")
            || (searchItem.type === "field_property" && item.unselectable)) {
            // click on the properties field itself or on a foldable property
            this.toggleItem(item, !item.isExpanded);
            return;
        }

        if (!item.unselectable) {
            const { searchItemId, label, operator, value } = item;
            this.env.searchModel.addAutoCompletionValues(searchItemId, { label, operator, value });
        }
        this.resetState();
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

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    /**
     * @param {Object} facet
     * @param {number} facetIndex
     * @param {KeyboardEvent} ev
     */
    onFacetKeydown(facet, facetIndex, ev) {
        switch (ev.key) {
            case "ArrowLeft": {
                if (facetIndex === 0) {
                    this.inputRef.el.focus();
                } else {
                    this.focusFacet(facetIndex - 1);
                }
                break;
            }
            case "ArrowRight": {
                const facets = this.root.el.getElementsByClassName("o_searchview_facet");
                if (facetIndex === facets.length - 1) {
                    this.inputRef.el.focus();
                } else {
                    this.focusFacet(facetIndex + 1);
                }
                break;
            }
            case "Backspace": {
                this.removeFacet(facet);
                break;
            }
        }
    }

    /**
     * @param {Object} facet
     */
    onFacetRemove(facet) {
        this.removeFacet(facet);
    }

    /**
     * @param {number} index
     */
    onItemMousemove(focusedIndex) {
        this.state.focusedIndex = focusedIndex;
        this.inputRef.el.focus();
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onSearchKeydown(ev) {
        if (ev.isComposing) {
            // This case happens with an IME for example: we let it handle all key events.
            return;
        }
        const focusedItem = this.items[this.state.focusedIndex];
        let focusedIndex;
        switch (ev.key) {
            case "ArrowDown":
                ev.preventDefault();
                if (this.items.length) {
                    if (this.state.focusedIndex >= this.items.length - 1) {
                        focusedIndex = 0;
                    } else {
                        focusedIndex = this.state.focusedIndex + 1;
                    }
                } else {
                    this.env.searchModel.trigger("focus-view");
                }
                break;
            case "ArrowUp":
                ev.preventDefault();
                if (this.items.length) {
                    if (
                        this.state.focusedIndex === 0 ||
                        this.state.focusedIndex > this.items.length - 1
                    ) {
                        focusedIndex = this.items.length - 1;
                    } else {
                        focusedIndex = this.state.focusedIndex - 1;
                    }
                }
                break;
            case "ArrowLeft":
                if (focusedItem && focusedItem.isParent && focusedItem.isExpanded) {
                    ev.preventDefault();
                    this.toggleItem(focusedItem, false);
                } else if (focusedItem && focusedItem.isChild) {
                    ev.preventDefault();
                    focusedIndex = this.items.findIndex(
                        (item) => item.isParent && item.searchItemId === focusedItem.searchItemId
                    );
                } else if (ev.target.selectionStart === 0) {
                    // focus rightmost facet if any.
                    this.focusFacet();
                } else {
                    // do nothing and navigate inside text
                }
                break;
            case "ArrowRight":
                if (ev.target.selectionStart === this.state.query.length) {
                    if (focusedItem && focusedItem.isParent) {
                        ev.preventDefault();
                        if (focusedItem.isExpanded) {
                            focusedIndex = this.state.focusedIndex + 1;
                        } else {
                            this.toggleItem(focusedItem, true);
                        }
                    } else if (ev.target.selectionStart === this.state.query.length) {
                        // Priority 3: focus leftmost facet if any.
                        this.focusFacet(0);
                    }
                }
                break;
            case "Backspace":
                if (!this.state.query.length) {
                    const facets = this.env.searchModel.facets;
                    if (facets.length) {
                        this.removeFacet(facets[facets.length - 1]);
                    }
                }
                break;
            case "Enter":
                if (!this.state.query.length) {
                    this.env.searchModel.search(); /** @todo keep this thing ?*/
                    break;
                } else if (focusedItem) {
                    ev.preventDefault(); // keep the focus inside the search bar
                    this.selectItem(focusedItem);
                }
                break;
            case "Tab":
                if (this.state.query.length && focusedItem) {
                    ev.preventDefault(); // keep the focus inside the search bar
                    this.selectItem(focusedItem);
                }
                break;
            case "Escape":
                this.resetState();
                break;
        }

        if (focusedIndex !== undefined) {
            this.state.focusedIndex = focusedIndex;
        }
    }

    /**
     * @param {InputEvent} ev
     */
    onSearchInput(ev) {
        const query = ev.target.value;
        if (query.trim()) {
            this.computeState({ query, expanded: [], focusedIndex: 0, subItems: [] });
        } else if (this.items.length) {
            this.resetState();
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    onWindowClick(ev) {
        if (this.items.length && !this.root.el.contains(ev.target)) {
            this.resetState();
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onWindowKeydown(ev) {
        if (this.items.length && ev.key === "Escape") {
            this.resetState();
        }
    }
}

SearchBar.template = "web.SearchBar";
SearchBar.props = {};
