odoo.define("web/static/src/js/views/search_panel_model_extension.js", function (require) {
    "use strict";

    const ActionModel = require("web/static/src/js/views/action_model.js");
    const { sortBy } = require("web.utils");
    const Domain = require("web.Domain");
    const pyUtils = require("web.py_utils");

    // DefaultViewTypes is the list of view types for which the searchpanel is
    // present by default (if not explicitly stated in the "view_types" attribute
    // in the arch).
    const DEFAULT_VIEW_TYPES = ["kanban", "tree"];
    const DEFAULT_LIMIT = 200;
    let nextSectionId = 1;

    /**
     * @param {Section} section
     * @returns {boolean}
     */
    function hasValues({ errorMsg, groups, type, values }) {
        if (errorMsg) {
            return true;
        } else if (groups) {
            return [...groups.values()].some((g) => g.values.size);
        } else if (type === "category") {
            return values && values.size > 1; // false item ignored
        } else {
            return values && values.size > 0;
        }
    }

    /**
     * @typedef Section
     * @prop {string} color
     * @prop {string} description
     * @prop {boolean} enableCounters
     * @prop {boolean} expand
     * @prop {string} fieldName
     * @prop {string} icon
     * @prop {number} id
     * @prop {number} index
     * @prop {number} limit
     * @prop {string} type
     */

    /**
     * @typedef {Section} Category
     * @prop {boolean} hierarchize
     */

    /**
     * @typedef {Section} Filter
     * @prop {string} domain
     * @prop {string} groupBy
     */

    /**
     * @function sectionPredicate
     * @param {Section} section
     * @returns {boolean}
     */

    /**
     * @property {{ sections: Map<number, Section> }} state
     * @extends ActionModel.Extension
     */
    class SearchPanelModelExtension extends ActionModel.Extension {
        constructor() {
            super(...arguments);

            this.searchDomain = null;
            this.DEFAULT_VALUE_INDEX = 0;
        }

        //---------------------------------------------------------------------
        // Public
        //---------------------------------------------------------------------

        /**
         * @override
         */
        exportState() {
            const state = super.exportState();
            state.sections = [...state.sections];
            for (const [id, section] of state.sections) {
                section.values = [...section.values];
                if (section.groups) {
                    section.groups = [...section.groups];
                    for (const [id, group] of section.groups) {
                        group.values = [...group.values];
                    }
                }
            }
            return state;
        }

        /**
         * @override
         * @returns {any}
         */
        get(property, ...args) {
            switch (property) {
                case "domain": return this.getDomain();
                case "sections": return this.getSections(...args);
            }
        }

        /**
         * @override
         */
        importState(importedState) {
            super.importState(...arguments);
            if (importedState) {
                this.state.sections = new Map(this.state.sections);
                for (const section of this.state.sections.values()) {
                    section.values = new Map(section.values);
                    if (section.groups) {
                        section.groups = new Map(section.groups);
                        for (const group of section.groups.values()) {
                            group.values = new Map(group.values);
                        }
                    }
                }
            }
        }

        /**
         * @override
         */
        async load() {
            await this._fetchSections({ initialLoad: true });
        }

        /**
         * @override
         */
        prepareState() {
            Object.assign(this.state, { sections: new Map() });
            this._createSectionsFromArch();
        }

        /**
         * @override
         */
        async reloadAfterDispatch() {
            await this._fetchSections();
        }

        //---------------------------------------------------------------------
        // Actions / Getters
        //---------------------------------------------------------------------

        /**
         * Returns the concatenation of the category domain ad the filter
         * domain.
         * @returns {Array[]}
         */
        getDomain() {
            return Domain.prototype.normalizeArray([
                ...this._getCategoryDomain(),
                ...this._getFilterDomain(),
            ]);
        }

        /**
         * Returns a sorted list of a copy of all sections. This list can be
         * filtered by a given predicate.
         * @param {sectionPredicate} [predicate] used to determine
         *      which subsets of sections is wanted
         * @returns {Section[]}
         */
        getSections(predicate) {
            let sections = [...this.state.sections.values()].map((section) =>
                Object.assign({}, section, { empty: !hasValues(section) })
            );
            if (predicate) {
                sections = sections.filter(predicate);
            }
            return sections.sort((s1, s2) => s1.index - s2.index);
        }

        /**
         * Sets the active value id of a given category. This will also update
         * the local storage value.
         * @param {number} sectionId
         * @param {number} valueId
         */
        toggleCategoryValue(sectionId, valueId) {
            const category = this.state.sections.get(sectionId);
            category.activeValueId = valueId;
            const storageKey = `searchpanel_${this.config.modelName}_${category.fieldName}`;
            this.env.services.local_storage.setItem(storageKey, valueId);
            // FIXME this should be removed (in another commit): should no longer (re)store
            // active category in localStorage
        }

        /**
         * Toggles a the filter value of a given section. The value will be set
         * to "forceTo" if provided, else it will be its own opposed value.
         * @param {number} sectionId
         * @param {number[]} valueIds
         * @param {boolean} [forceTo=null]
         */
        toggleFilterValues(sectionId, valueIds, forceTo = null) {
            const section = this.state.sections.get(sectionId);
            for (const valueId of valueIds) {
                const value = section.values.get(valueId);
                value.checked = forceTo === null ? !value.checked : forceTo;
            }
        }

        //---------------------------------------------------------------------
        // Internal getters
        //---------------------------------------------------------------------

        /**
         * Shorthand access to sections of type "category".
         * @returns {Category[]}
         */
        get categories() {
            return [...this.state.sections.values()].filter(s => s.type === "category");
        }

        /**
         * Shorthand access to sections of type "filter".
         * @returns {Filter[]}
         */
        get filters() {
            return [...this.state.sections.values()].filter(s => s.type === "filter");
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * Sets active values for each filter (coming from context). This needs
         * to be done only once at initialization.
         * @private
         */
        _applyDefaultFilterValues() {
            for (const { fieldName, values } of this.filters) {
                const defaultValues = this.config.defaultValues[fieldName] || [];
                for (const valueId of defaultValues) {
                    const value = values.get(valueId);
                    if (value) {
                        value.checked = true;
                    }
                }
            }
        }

        /**
         * @private
         * @param {string} sectionId
         * @param {Object} result
         */
        _createCategoryTree(sectionId, result) {
            const category = this.state.sections.get(sectionId);

            let { error_msg, parent_field: parentField, values, } = result;
            if (error_msg) {
                category.errorMsg = error_msg;
                values = [];
            }
            if (category.hierarchize) {
                category.parentField = parentField;
            }

            const allItem = {
                childrenIds: [],
                display_name: this.env._t("All"),
                id: false,
                bold: true,
                parentId: false,
            };
            category.values = new Map([[false, allItem]]);
            for (const value of values) {
                category.values.set(
                    value.id,
                    Object.assign({}, value, {
                        childrenIds: [],
                        parentId: value[parentField] || false,
                    })
                );
            }
            for (const value of values) {
                const { parentId } = category.values.get(value.id);
                if (parentId && category.values.has(parentId)) {
                    category.values.get(parentId).childrenIds.push(value.id);
                }
            }
            // collect rootIds
            category.rootIds = [false];
            for (const value of values) {
                const { parentId } = category.values.get(value.id);
                if (!parentId) {
                    category.rootIds.push(value.id);
                }
            }
            // Set active value from context
            category.activeValueId = this._getCategoryDefaultValue(values, category);
        }

        /**
         * @private
         * @param {string} sectionId
         * @param {Object} result
         */
        _createFilterTree(sectionId, result) {
            const filter = this.state.sections.get(sectionId);

            let { error_msg, values, } = result;
            if (error_msg) {
                filter.errorMsg = error_msg;
                values = [];
            }

            // restore checked property
            values.forEach((value) => {
                const oldValue = filter.values && filter.values.get(value.id);
                value.checked = (oldValue && oldValue.checked) || false;
            });

            filter.values = new Map();
            const groupIds = [];
            if (filter.groupBy) {
                const groups = new Map();
                for (const value of values) {
                    const groupId = value.group_id;
                    if (!groups.has(groupId)) {
                        if (groupId) {
                            groupIds.push(groupId);
                        }
                        groups.set(groupId, {
                            id: groupId,
                            name: value.group_name,
                            values: new Map(),
                            tooltip: value.group_tooltip,
                            sequence: value.group_sequence,
                            hex_color: value.group_hex_color,
                        });
                        // restore former checked state
                        const oldGroup =
                            filter.groups && filter.groups.get(groupId);
                        groups.get(groupId).state =
                            (oldGroup && oldGroup.state) || false;
                    }
                    groups.get(groupId).values.set(value.id, value);
                }
                filter.groups = groups;
                filter.sortedGroupIds = sortBy(
                    groupIds,
                    (id) => groups.get(id).sequence || groups.get(id).name
                );
                for (const group of filter.groups.values()) {
                    for (const [valueId, value] of group.values) {
                        filter.values.set(valueId, value);
                    }
                }
            } else {
                for (const value of values) {
                    filter.values.set(value.id, value);
                }
            }
        }

        /**
         * Adds a section in this.state.sections for each visible field found
         * in the search panel arch.
         * @private
         */
        _createSectionsFromArch() {
            this.config.archNodes.forEach(({ attrs, tag }, index) => {
                if (tag !== "field" || attrs.invisible === "1") {
                    return;
                }
                const type = attrs.select === "multi" ? "filter" : "category";
                const section = {
                    color: attrs.color,
                    description:
                        attrs.string || this.config.fields[attrs.name].string,
                    enableCounters: !!pyUtils.py_eval(
                        attrs.enable_counters || "0"
                    ),
                    expand: !!pyUtils.py_eval(attrs.expand || "0"),
                    fieldName: attrs.name,
                    icon: attrs.icon,
                    id: nextSectionId++,
                    index,
                    limit: pyUtils.py_eval(attrs.limit || String(DEFAULT_LIMIT)),
                    type,
                };
                if (type === "category") {
                    section.icon = section.icon || "fa-folder";
                    section.hierarchize = !!pyUtils.py_eval(
                        attrs.hierarchize || "1"
                    );
                } else {
                    section.domain = attrs.domain || "[]";
                    section.groupBy = attrs.groupby;
                    section.icon = section.icon || "fa-filter";
                }
                this.state.sections.set(section.id, section);
            });
        }

        /**
         * Fetches values for each category at startup. At reload a category is
         * only fetched if needed.
         * @private
         * @param {{
         *      initialLoad: boolean,
         *      searchDomainHasChanged: boolean
         *  }} options
         * @returns {Promise} resolved when all categories have been fetched
         */
        async _fetchCategories({ initialLoad, searchDomainHasChanged }) {
            const proms = [];
            for (const category of this.categories) {
                const { enableCounters, expand, hierarchize, limit } = category;
                if (initialLoad || enableCounters || (searchDomainHasChanged && !expand)) {
                    const prom = this.env.services.rpc({
                        method: "search_panel_select_range",
                        model: this.config.modelName,
                        args: [category.fieldName],
                        kwargs: {
                            category_domain: this._getCategoryDomain(
                                category.id
                            ),
                            enable_counters: enableCounters,
                            expand,
                            filter_domain: this._getFilterDomain(),
                            hierarchize,
                            limit,
                            search_domain: this.searchDomain,
                        },
                    }).then(result => this._createCategoryTree(category.id, result));
                    proms.push(prom);
                }
            }
            await Promise.all(proms);
        }

        /**
         * Fetches values for each filter. This is done at startup and at each
         * reload if needed.
         * @private
         * @param {{
         *      initialLoad: boolean,
         *      searchDomainHasChanged: boolean
         *  }} options
         * @returns {Promise} resolved when all filters have been fetched
         */
        async _fetchFilters({ initialLoad, searchDomainHasChanged }) {
            const evalContext = {};
            for (const category of this.categories) {
                evalContext[category.fieldName] = category.activeValueId;
            }
            const categoryDomain = this._getCategoryDomain();
            const proms = [];
            for (const filter of this.filters) {
                const { enableCounters, expand, groupBy, limit } = filter;
                if (initialLoad || enableCounters || (searchDomainHasChanged && !expand)) {
                    const prom = this.env.services.rpc({
                        method: "search_panel_select_multi_range",
                        model: this.config.modelName,
                        args: [filter.fieldName],
                        kwargs: {
                            category_domain: categoryDomain,
                            comodel_domain: Domain.prototype.stringToArray(
                                filter.domain,
                                evalContext
                            ),
                            enable_counters: enableCounters,
                            filter_domain: this._getFilterDomain(filter.id),
                            expand,
                            group_by: groupBy || false,
                            group_domain: this._getGroupDomain(filter),
                            limit,
                            search_domain: this.searchDomain,
                        },
                    }).then(result => this._createFilterTree(filter.id, result));
                    proms.push(prom);
                }
            }
            await Promise.all(proms);
        }

        /**
         * Fetches categories and filters at startup or if needed.
         * @private
         * @param {Object} [options={}]
         * @param {boolean} [options.initialLoad=false]
         */
        async _fetchSections(options = {}) {
            const searchDomain = this._getExternalDomain();
            if (!options.initialLoad) {
                options.searchDomainHasChanged =
                    JSON.stringify(this.searchDomain) !== JSON.stringify(searchDomain);
            }
            this.searchDomain = searchDomain;
            await this._fetchCategories(options);
            await this._fetchFilters(options);
            if (options.initialLoad) {
                this._applyDefaultFilterValues();
            }
        }

        /**
         * Computes and returns the domain based on the current active
         * categories. If "excludedCategoryId" is provided, the category with
         * that id is not taken into account in the domain computation.
         * @private
         * @param {string} [excludedCategoryId]
         * @returns {Array[]}
         */
        _getCategoryDomain(excludedCategoryId) {
            const domain = [];
            for (const category of this.categories) {
                if (
                    category.id === excludedCategoryId ||
                    category.activeValueId === false
                ) {
                    continue;
                }
                if (category.activeValueId) {
                    const field = this.config.fields[category.fieldName];
                    const operator =
                        field.type === "many2one" && category.parentField ? "child_of" : "=";
                    domain.push([
                        category.fieldName,
                        operator,
                        category.activeValueId,
                    ]);
                }
            }
            return domain;
        }

        /**
         * @private
         * @param {Object[]} values
         * @param {Category} category
         * @returns {number | false}
         */
        _getCategoryDefaultValue(values, { fieldName }) {
            const validValues = [false, ...values.map((val) => val.id)];
            const defaultValue = this.config.defaultValues[fieldName];
            if (validValues.includes(defaultValue)) {
                return defaultValue;
            }
            if (this.config.defaultNoFilter) {
                return false;
            }
            // If not set in context, or set to an unknown value, set active value
            // from localStorage
            const storageKey = `searchpanel_${this.config.modelName}_${fieldName}`;
            const storageValue = this.env.services.local_storage.getItem(storageKey);
            if (validValues.includes(storageValue)) {
                return storageValue;
            }
            // If still not a valid value, get the search panel default value
            // from the given valid values.
            return validValues[
                Math.min(validValues.length - 1, this.DEFAULT_VALUE_INDEX)
            ];
        }

        /**
         * Returns the domain retrieved from the other model extensions.
         * @private
         * @returns {Array[]}
         */
        _getExternalDomain() {
            const domains = this.config.get("domain");
            const domain = domains.reduce((acc, dom) => [...acc, ...dom], []);
            return Domain.prototype.normalizeArray(domain);
        }

        /**
         * Computes and returns the domain based on the current checked
         * filters. The values of a single filter are combined using a simple
         * rule: checked values within a same group are combined with an "OR"
         * operator (this is expressed as single condition using a list) and
         * groups are combined with an "AND" operator (expressed by
         * concatenation of conditions).
         * If a filter has no group, its checked values are implicitely
         * considered as forming a group (and grouped using an "OR").
         * If excludedFilterId is provided, the filter with that id is not
         * taken into account in the domain computation.
         * @private
         * @param {string} [excludedFilterId]
         * @returns {Array[]}
         */
        _getFilterDomain(excludedFilterId) {
            const domain = [];

            function addCondition(fieldName, valueMap) {
                const ids = [];
                for (const [valueId, value] of valueMap) {
                    if (value.checked) {
                        ids.push(valueId);
                    }
                }
                if (ids.length) {
                    domain.push([fieldName, "in", ids]);
                }
            }

            for (const filter of this.filters) {
                if (filter.id === excludedFilterId) {
                    continue;
                }
                const { fieldName, groups, values } = filter;
                if (groups) {
                    for (const group of groups.values()) {
                        addCondition(fieldName, group.values);
                    }
                } else if (values) {
                    addCondition(fieldName, values);
                }
            }
            return domain;
        }

        /**
         * Returns a domain or an object of domains used to complement
         * the filter domains to accurately describe the constrains on
         * records when computing record counts associated to the filter
         * values (if a groupBy is provided). The idea is that the checked
         * values within a group should not impact the counts for the other
         * values in the same group.
         * @private
         * @param {string} filter
         * @returns {Object<string, Array[]> | Array[] | null}
         */
        _getGroupDomain(filter) {
            const { fieldName, groups, enableCounters } = filter;
            const { type: fieldType } = this.config.fields[fieldName];

            if (!enableCounters || !groups) {
                return {
                    many2one: [],
                    many2many: {},
                }[fieldType];
            }
            let groupDomain = null;
            if (fieldType === "many2one") {
                for (const group of groups.values()) {
                    const valueIds = [];
                    let active = false;
                    for (const [valueId, value] of group.values) {
                        const { checked } = value;
                        valueIds.push(valueId);
                        if (checked) {
                            active = true;
                        }
                    }
                    if (active) {
                        if (groupDomain) {
                            groupDomain = [[0, "=", 1]];
                            break;
                        } else {
                            groupDomain = [[fieldName, "in", valueIds]];
                        }
                    }
                }
            } else if (fieldType === "many2many") {
                const checkedValueIds = new Map();
                groups.forEach(({ values }, groupId) => {
                    values.forEach(({ checked }, valueId) => {
                        if (checked) {
                            if (!checkedValueIds.has(groupId)) {
                                checkedValueIds.set(groupId, []);
                            }
                            checkedValueIds.get(groupId).push(valueId);
                        }
                    });
                });
                groupDomain = {};
                for (const [gId, ids] of checkedValueIds.entries()) {
                    for (const groupId of groups.keys()) {
                        if (gId !== groupId) {
                            const key = JSON.stringify(groupId);
                            if (!groupDomain[key]) {
                                groupDomain[key] = [];
                            }
                            groupDomain[key].push([fieldName, "in", ids]);
                        }
                    }
                }
            }
            return groupDomain;
        }

        //---------------------------------------------------------------------
        // Static
        //---------------------------------------------------------------------

        /**
         * @override
         * @returns {{ attrs: Object, children: Object[] } | null}
         */
        static extractArchInfo(archs, viewType) {
            const { children } = archs.search;
            const spNode = children.find(c => c.tag === "searchpanel");
            const isObject = (obj) => typeof obj === "object" && obj !== null;
            if (spNode) {
                const actualType = viewType === "list" ? "tree" : viewType;
                const { view_types } = spNode.attrs;
                const viewTypes = view_types ?
                    view_types.split(",") :
                    DEFAULT_VIEW_TYPES;
                if (viewTypes.includes(actualType)) {
                    return {
                        attrs: spNode.attrs,
                        children: spNode.children.filter(isObject),
                    };
                }
            }
            return null;
        }
    }
    SearchPanelModelExtension.layer = 1;

    ActionModel.registry.add("SearchPanel", SearchPanelModelExtension, 30);

    return SearchPanelModelExtension;
});
