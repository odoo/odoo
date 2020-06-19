odoo.define('web.SearchPanel', function (require) {
"use strict";

/**
 * This file defines the SearchPanel widget for Kanban. It allows to
 * filter/manage data easily.
 */

const core = require('web.core');
const Domain = require('web.Domain');
const pyUtils = require('web.py_utils');
const { sortBy } = require('web.utils');
const viewUtils = require('web.viewUtils');
const Widget = require('web.Widget');

const qweb = core.qweb;

// defaultViewTypes is the list of view types for which the searchpanel is
// present by default (if not explicitly stated in the 'view_types' attribute
// in the arch)
const defaultViewTypes = ['kanban', 'tree'];
let nextSectionId = 1;

const SEARCH_PANEL_DEFAULT_LIMIT = 200;

/**
 * Given a <searchpanel> arch node, iterate over its children to generate the
 * description of each section (being either a category or a filter).
 *
 * @param {Object} node a <searchpanel> arch node
 * @param {Object} fields the fields of the model
 * @returns {Object}
 */
function _processSearchPanelNode(node, fields) {
    const sections = {};
    node.children.forEach(({ attrs, tag }, index) => {
        if (tag !== 'field' || attrs.invisible === "1") {
            return;
        }
        const fieldName = attrs.name;
        const type = attrs.select === 'multi' ? 'filter' : 'category';

        const sectionId = `section_${nextSectionId++}`;
        const section = {
            color: attrs.color,
            description: attrs.string || fields[fieldName].string,
            enableCounters: !!pyUtils.py_eval(attrs.enable_counters || '0'),
            expand: !!pyUtils.py_eval(attrs.expand || '0'),
            fieldName,
            icon: attrs.icon,
            id: sectionId,
            index,
            limit: attrs.limit ?
                pyUtils.py_eval(attrs.limit) :
                SEARCH_PANEL_DEFAULT_LIMIT,
            type,
        };
        if (section.type === 'category') {
            section.icon = section.icon || 'fa-folder';
            section.hierarchize = !!pyUtils.py_eval(attrs.hierarchize || '1');
        } else if (section.type === 'filter') {
            section.domain = attrs.domain || '[]';
            section.groupBy = attrs.groupby;
            section.icon = section.icon || 'fa-filter';
        }
        sections[sectionId] = section;
    });
    return sections;
}

const SearchPanel = Widget.extend({
    className: 'o_search_panel',
    events: {
        'click .o_search_panel_category_value header': '_onCategoryValueClicked',
        'change .o_search_panel_filter_value > header > div > input': '_onFilterValueChanged',
        'change .o_search_panel_filter_group > header > div > input': '_onFilterGroupChanged',
    },

    /**
     * @constructor
     * @param {Object} params
     * @param {Object} [params.defaultValues={}] the value(s) to activate by
     *   default, for each filter and category
     * @param {boolean} [params.defaultNoFilter=false] if true, select 'All' as
     *   value for each category that has no value specified in defaultValues
     *   (instead of looking in the localStorage for the last selected value)
     * @param {Object} params.fields
     * @param {string} params.model
     * @param {Array[]} params.searchDomain domain coming from controlPanel
     * @param {Array[]} params.viewDomain domain coming from the view (ill advised)
     * @param {Object} params.sections
     * @param {Object} [params.state] state exported by another searchpanel
     *   instance
     */
    init(parent, params) {
        this._super(...arguments);

        this.categories = {};
        this.filters = {};
        for (const section of Object.values(params.sections)) {
            const key = section.type === 'category' ? 'categories' : 'filters';
            this[key][section.id] = section;
        }

        this.initialState = params.state;
        this.scrollTop = this.initialState && this.initialState.scrollTop || null;
        this.defaultValues = params.defaultValues || {};
        if (params.defaultNoFilter) {
            Object.values(this.categories).forEach(({ fieldName }) => {
                this.defaultValues[fieldName] = this.defaultValues[fieldName] || false;
            });
        }
        this.fields = params.fields;
        this.model = params.model;
        this.className = params.classes.concat(['o_search_panel']).join(' ');
        this.reloadOptions = null;
        this.searchDomain = params.searchDomain;
        this.viewDomain = params.viewDomain;
    },
    /**
     * @override
     */
    async willStart() {
        const _super = this._super;
        if (this.initialState) {
            this.filters = this.initialState.filters;
            this.categories = this.initialState.categories;
        } else {
            await this._fetchCategories(true);
            await this._fetchFilters();
            await this._applyDefaultFilterValues();
        }
        return _super.call(this, ...arguments);
    },
    /**
     * @override
     */
    start() {
        this._render();
        return this._super(...arguments);
    },
    /**
     * Called each time the searchPanel is attached into the DOM.
     */
    on_attach_callback() {
        if (this.scrollTop !== null) {
            this.el.scrollTop = this.scrollTop;
        }
    },

    //-------------------------------------------------------------------------
    // Public
    //-------------------------------------------------------------------------

    /**
     * Parse a given search view arch to extract the searchpanel information
     * (i.e. a description of each filter/category). Note that according to the
     * 'view_types' attribute on the <searchpanel> node, and the given viewType,
     * it may return undefined, meaning that no searchpanel should be rendered
     * for the current view.
     *
     * Note that this is static method, called by AbstractView, *before*
     * instantiating the SearchPanel, as depending on what it returns, we may
     * or may not instantiate a SearchPanel.
     *
     * @static
     * @param {Object} viewInfo the viewInfo of a search view
     * @param {string} viewInfo.arch
     * @param {Object} viewInfo.fields
     * @param {string} viewType the type of the current view (e.g. 'kanban')
     * @returns {Object}
     */
    computeSearchPanelParams(arch, fields, viewType) {
        const searchPanelParams = {};
        if (arch && fields) {
            const parsedArch = viewUtils.parseArch(arch);
            const searchPanelNode = parsedArch.children.find(child => child.tag === 'searchpanel');
            if (searchPanelNode) {
                const { attrs } = searchPanelNode;
                const type = viewType === 'list' ? 'tree' : viewType;
                let viewTypes = defaultViewTypes;
                if (attrs.view_types) {
                    viewTypes = attrs.view_types.split(',');
                }
                if (attrs.class) {
                    searchPanelParams.classes = attrs.class.split(' ');
                }
                if (viewTypes.includes(type)) {
                    searchPanelParams.sections = _processSearchPanelNode(searchPanelNode, fields);
                }
            }
        }
        return searchPanelParams;
    },
    /**
     * Export the current state (categories and filters) of the searchpanel.
     *
     * @returns {Object}
     */
    exportState() {
        return {
            categories: this.categories,
            filters: this.filters,
            scrollTop: this.el ? this.el.scrollTop : null,
        };
    },
    /**
     * @returns {Array[]} the current searchPanel domain based on active
     *   categories and checked filters
     */
    getDomain() {
        return this._getCategoryDomain().concat(this._getFilterDomain());
    },
    /**
     * Import a previously exported state (see exportState).
     *
     * @param {Object} state
     * @param {Object} state.filters.
     * @param {Object} state.categories
     */
    importState(state) {
        this.categories = state.categories || this.categories;
        this.filters = state.filters || this.filters;
        this.scrollTop = state.scrollTop;
        this._render();
    },
    /**
     * Reload the filters and categories and re-render. Note that we only reload them
     * if the controlPanel domain or searchPanel domain has changed.
     *
     * @param {Object} params
     * @param {Array[]} params.searchDomain domain coming from controlPanel
     * @param {Array[]} params.viewDomain domain coming from view
     * @returns {Promise}
     */
    async update(params) {
        const currentDomain = JSON.stringify([...this.searchDomain, ...this.viewDomain]);
        const newDomain = JSON.stringify([...params.searchDomain, ...params.viewDomain]);
        if (this.reloadOptions || (currentDomain !== newDomain)) {
            this.searchDomain = params.searchDomain;
            this.viewDomain = params.viewDomain;
            if (!this.reloadOptions || this.reloadOptions.shouldFetchCategories) {
                await this._fetchCategories();
            }
            await this._fetchFilters();
            this.reloadOptions = null;
        }
        return this._render();
    },

    //-------------------------------------------------------------------------
    // Private
    //-------------------------------------------------------------------------

    /**
     * Set active values for each filter (coming from context). This needs to be
     * done only once, at widget startup.
     *
     * @private
     */
    _applyDefaultFilterValues() {
        Object.values(this.filters).forEach(filter => {
            const defaultValues = this.defaultValues[filter.fieldName] || [];
            defaultValues.forEach(value => {
                if (filter.values[value]) {
                    filter.values[value].checked = true;
                }
            });
            Object.values(filter.groups || []).forEach(this._updateFilterGroupState);
        });
    },
    /**
     * @private
     * @param {string} categoryId
     * @param {Object} result
     */
    _createCategoryTree(categoryId, result) {
        const category = this.categories[categoryId];
        let { error_msg, parent_field: parentField, values } = result;
        if (error_msg) {
            category.errorMsg = error_msg;
            values = [];
        }
        if (category.hierarchize) {
            category.parentField = parentField;
        }

        const unfoldedIds = Object.values(category.values || {})
            .filter(c => c.folded === false)
            .map(c => c.id);

        category.values = {};
        values.forEach(value => {
            category.values[value.id] = Object.assign({}, value, {
                childrenIds: [],
                folded: !unfoldedIds.includes(value.id),
                parentId: value[parentField] || false,
            });
        });
        values.forEach(value => {
            const { parentId: parentCategoryId } = category.values[value.id];
            if (parentCategoryId && parentCategoryId in category.values) {
                category.values[parentCategoryId].childrenIds.push(value.id);
            }
        });
        category.rootIds = [];
        for (const value of values) {
            const { parentId } = category.values[value.id];
            if (!parentId) {
                category.rootIds.push(value.id);
            }
        }

        // set active value
        const validValues = [...Object.values(category.values).map(v => v.id), false];
        const value = this._getCategoryDefaultValue(category, validValues);
        category.activeValueId = validValues.includes(value) ? value : false;

        // unfold ancestor values of active value to make it is visible
        if (category.activeValueId) {
            const parentValueIds = this._getAncestorValueIds(category, category.activeValueId);
            parentValueIds.forEach(parentValue => {
                category.values[parentValue].folded = false;
            });
        }
    },
    /**
     * @private
     * @param {string} filterId
     * @param {Object} result
     */
    _createFilterTree(filterId, result) {
        const filter = this.filters[filterId];
        let { error_msg, values } = result;
        if (error_msg) {
            filter.errorMsg = error_msg;
            values = [];
        }

        // restore checked property
        values.forEach(value => {
            const oldValue = filter.values && filter.values[value.id];
            value.checked = oldValue && oldValue.checked || false;
        });

        filter.values = {};
        const groupIds = [];
        if (filter.groupBy) {
            const groups = {};
            values.forEach(value => {
                const groupId = JSON.stringify(value.group_id);
                if (!groups[groupId]) {
                    if (groupId !== 'false') {
                        groupIds.push(groupId);
                    }
                    groups[groupId] = {
                        folded: false,
                        id: groupId,
                        name: value.group_name,
                        values: {},
                        tooltip: value.group_tooltip,
                        sequence: value.group_sequence,
                        hex_color: value.group_hex_color,
                        sortedValueIds: [],
                    };
                    // restore former checked and folded state
                    const oldGroup = filter.groups && filter.groups[groupId];
                    groups[groupId].state = oldGroup && oldGroup.state || false;
                    groups[groupId].folded = oldGroup && oldGroup.folded || false;
                }
                groups[groupId].values[value.id] = value;
                groups[groupId].sortedValueIds.push(value.id);
            });
            filter.groups = groups;
            filter.sortedGroupIds = sortBy(groupIds,
                id => groups[id].sequence || groups[id].name
            );
            Object.values(filter.groups).forEach(group => {
                Object.assign(filter.values, group.values);
            });
        } else {
            values.forEach(value => {
                filter.values[value.id] = value;
            });
            filter.sortedValueIds = values.map(value => value.id);
        }
    },
    /**
     * Fetch values for each category at startup. At reload a category is only
     * fetched if the searchDomain changes and displayCounters is true for it.
     *
     * @private
     * @param {boolean} [force]
     * @returns {Promise} resolved when all categories have been fetched
     */
    _fetchCategories(force) {
        const proms = [];
        for (const category of Object.values(this.categories)) {
            const { enableCounters, expand, hierarchize, limit } = category;
            if (force || enableCounters) {
                const prom = this._rpc({
                    method: 'search_panel_select_range',
                    model: this.model,
                    args: [category.fieldName],
                    kwargs: {
                        category_domain: this._getCategoryDomain(category.id),
                        enable_counters: enableCounters,
                        expand,
                        filter_domain: this._getFilterDomain(),
                        hierarchize,
                        limit,
                        search_domain: this.searchDomain,
                    },
                }).then(
                    (result) => this._createCategoryTree(category.id, result)
                );
                proms.push(prom);
            }
        }
        return Promise.all(proms);
    },
    /**
     * Fetch values for each filter. This is done at startup, and at each reload
     * (when the controlPanel or searchPanel domain changes).
     *
     * @private
     * @returns {Promise} resolved when all filters have been fetched
     */
    _fetchFilters() {
        const evalContext = {};
        for (const category of Object.values(this.categories)) {
            evalContext[category.fieldName] = category.activeValueId;
        }
        const categoryDomain = this._getCategoryDomain();
        const proms = [];
        for (const filter of Object.values(this.filters)) {
            const { enableCounters, expand, groupBy, limit } = filter;
            const prom = this._rpc({
                method: 'search_panel_select_multi_range',
                model: this.model,
                args: [filter.fieldName],
                kwargs: {
                    category_domain: categoryDomain,
                    comodel_domain: Domain.prototype.stringToArray(filter.domain, evalContext),
                    enable_counters: enableCounters,
                    filter_domain: this._getFilterDomain(filter.id),
                    expand,
                    group_by: groupBy || false,
                    group_domain: this._getGroupDomain(filter),
                    limit,
                    search_domain: [...this.searchDomain, ...this.viewDomain],
                },
            }).then(
                (result) => this._createFilterTree(filter.id, result)
            );
            proms.push(prom);
        }
        return Promise.all(proms);
    },
    /**
     * @private
     * @param {Object} category
     * @param {Array} validValues
     * @returns {(number|boolean)} id of the default item of the category or false
     */
    _getCategoryDefaultValue(category, validValues) {
        // set active value from context
        const value = this.defaultValues[category.fieldName];
        // if not set in context, or set to an unknown value, set active value
        // from localStorage
        if (!validValues.includes(value)) {
            const storageKey = this._getLocalStorageKey(category);
            return this.call('local_storage', 'getItem', storageKey);
        }
        return value;
    },
    /**
     * Compute and return the domain based on the current active categories.
     *
     * @private
     * @param {string} [excludedCategoryId]
     * @returns {Array[]}
     */
    _getCategoryDomain(excludedCategoryId) {
        const domain = [];
        for (const category of Object.values(this.categories)) {
            if (category.id === excludedCategoryId) {
                continue;
            }
            if (category.activeValueId) {
                const field = this.fields[category.fieldName];
                const op = (field.type === 'many2one' && category.parentField) ? 'child_of' : '=';
                domain.push([category.fieldName, op, category.activeValueId]);
            }
        }
        return domain;
    },
    /**
     * Compute and return the domain based on the current checked filters.
     * The values of a single filter are combined using a simple rule: checked values within
     * a same group are combined with an 'OR' (this is expressed as single condition using a list)
     * and groups are combined with an 'AND' (expressed by concatenation of conditions).
     * If a filter has no groups, its checked values are implicitely considered as forming
     * a group (and grouped using an 'OR').
     *
     * @private
     * @param {string} [excludedFilterId]
     * @returns {Array[]}
     */
    _getFilterDomain(excludedFilterId) {
        const domain = [];

        function addCondition(fieldName, checkedValues) {
            if (checkedValues.length) {
                const ids = checkedValues.map(v => v.id);
                domain.push([fieldName, 'in', ids]);
            }
        }

        for (const filter of Object.values(this.filters)) {
            if (filter.id === excludedFilterId) {
                continue;
            }
            const { fieldName } = filter;
            let checkedValues;
            if (filter.groups) {
                for (const group of Object.values(filter.groups)) {
                    checkedValues = Object.values(group.values).filter(v => v.checked);
                    addCondition(fieldName, checkedValues);
                }
            } else if (filter.values) {
                checkedValues = Object.values(filter.values).filter(v => v.checked);
                addCondition(fieldName, checkedValues);
            }
        }
        return domain;
    },
    /**
     * Returns a domain or an object of domains used to complement
     * the filter domains to accurately describe the constraints on
     * records when computing record counts associated with the filter
     * values (if a groupBy is provided). The idea is that the checked values
     * within a group should not impact the counts for the other values
     * in the same group.
     *
     * @private
     * @param {string} filter
     * @returns {(Array{}|Array[]|undefined)}
     */
    _getGroupDomain(filter) {
        const { fieldName, groups, enableCounters } = filter;
        const { type: fieldType } = this.fields[fieldName];

        if (!enableCounters || !groups) {
            switch (fieldType) {
                case 'many2one': return [];
                case 'many2many': return {};
                default: return;
            }
        }

        let groupDomain;
        if (fieldType === 'many2one') {
            for (const group of Object.values(groups)) {
                const valueIds = [];
                let active = false;
                for (const value of Object.values(group.values || {})) {
                    const { id, checked } = value;
                    valueIds.push(id);
                    if (checked) {
                        active = true;
                    }
                }
                if (active) {
                    if (groupDomain) {
                        groupDomain = Domain.FALSE_DOMAIN;
                        break;
                    } else {
                        groupDomain = [[fieldName, 'in', valueIds]];
                    }
                }
            }
        } else if (fieldType === 'many2many') {
            const checkedValueIds = {};
            for (const group of Object.values(groups)) {
                for (const value of Object.values(group.values || {})) {
                    const { id, checked } = value;
                    if (checked) {
                        if (!checkedValueIds[group.id]) {
                            checkedValueIds[group.id] = [];
                        }
                        checkedValueIds[group.id].push(id);
                    }
                }
            }
            groupDomain = {};
            for (const gId in checkedValueIds) {
                const ids = checkedValueIds[gId];
                for (const group of Object.values(groups)) {
                    if (gId !== group.id) {
                        if (!groupDomain[group.id]) {
                            groupDomain[group.id] = [];
                        }
                        groupDomain[group.id].push(
                            [fieldName, 'in', ids]
                        );
                    }
                }
            }
        }
        return groupDomain;
    },
    /**
     * The active id of each category is stored in the localStorage, s.t. it
     * can be restored afterwards (when the action is reloaded, for instance).
     * This function returns the key in the sessionStorage for a given category.
     *
     * @param {Object} category
     * @returns {string}
     */
    _getLocalStorageKey(category) {
        return 'searchpanel_' + this.model + '_' + category.fieldName;
    },
    /**
     * @private
     * @param {Object} category
     * @param {number} categoryValueId
     * @returns {number[]} list of ids of the ancestors of the given value in
     *   the given category
     */
    _getAncestorValueIds(category, categoryValueId) {
        const { parentId } = category.values[categoryValueId];
        if (parentId) {
            return [parentId].concat(this._getAncestorValueIds(category, parentId));
        }
        return [];
    },
    /**
     * Compute the current searchPanel domain based on categories and filters,
     * and notify environment of the domain change.
     *
     * Note that this assumes that the environment will update the searchPanel.
     * This is done as such to ensure the coordination between the reloading of
     * the searchPanel and the reloading of the data.
     *
     * @private
     */
    _notifyDomainUpdated() {
        this.reloadOptions = { shouldFetchCategories: true };
        this.trigger_up('search_panel_domain_updated', {
            domain: this.getDomain(),
        });
    },
    /**
     * @private
     */
    _render() {
        this.$el.empty();

        // sort categories and filters according to their index
        const categories = Object.values(this.categories);
        const filters = Object.values(this.filters);
        const sections = categories.concat(filters).sort((s1, s2) => s1.index - s2.index);

        sections.forEach(section => {
            if (Object.keys(section.values).length || section.errorMsg) {
                if (section.type === 'category') {
                    this.$el.append(this._renderCategory(section));
                } else {
                    this.$el.append(this._renderFilter(section));
                }
            }
        });
    },
    /**
     * @private
     * @param {Object} category
     * @returns {string}
     */
    _renderCategory(category) {
        return qweb.render('SearchPanel.Category', { category });
    },
    /**
     * @private
     * @param {Object} filter
     * @returns {HTMLElement}
     */
    _renderFilter(filter) {
        const filterElement = $(qweb.render('SearchPanel.Filter', { filter }))[0];

        // set group inputs in indeterminate state when necessary
        Object.keys(filter.groups || {}).forEach(groupId => {
            const group = filter.groups[groupId];
            const { state } = group;
            // group 'false' is not displayed
            if (groupId !== 'false' && state === 'indeterminate') {
                const sel = `.o_search_panel_filter_group[data-group-id="${groupId}"] input`;
                filterElement.querySelector(sel).indeterminate = true;
            }
        });

        return filterElement;
    },
    /**
     * Updates the state property of a given filter's group according to the
     * checked property of its values.
     *
     * @private
     * @param {Object} group
     */
    _updateFilterGroupState(group) {
        if (Object.values(group.values).some(v => v.checked)) {
            if (Object.values(group.values).some(v => !v.checked)) {
                group.state = 'indeterminate';
            } else {
                group.state = 'checked';
            }
        } else {
            group.state = 'unchecked';
        }
    },

    //-------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onCategoryValueClicked(ev) {
        ev.stopPropagation();
        const item = ev.currentTarget.closest('.o_search_panel_category_value');
        const category = this.categories[item.dataset.categoryId];
        const valueId = !isNaN(item.dataset.id) ?
            Number(item.dataset.id) :
            item.dataset.id || false;
        const hasChanged = category.activeValueId !== valueId;
        category.activeValueId = valueId;
        const value = category.values[category.activeValueId];
        if (value) {
            value.folded = value.folded ? false : !hasChanged;
        }
        if (hasChanged) {
            const storageKey = this._getLocalStorageKey(category);
            this.call('local_storage', 'setItem', storageKey, valueId);
            this._notifyDomainUpdated();
        } else {
            this._render();
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onFilterGroupChanged(ev) {
        ev.stopPropagation();
        const item = ev.target.closest('.o_search_panel_filter_group');
        const filter = this.filters[item.dataset.filterId];
        const group = filter.groups[item.dataset.groupId];
        group.state = group.state === 'checked' ? 'unchecked' : 'checked';
        Object.values(group.values).forEach(value => {
            value.checked = group.state === 'checked';
        });
        this._notifyDomainUpdated();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onFilterValueChanged(ev) {
        ev.stopPropagation();
        const item = ev.target.closest('.o_search_panel_filter_value');
        const filter = this.filters[item.dataset.filterId];
        const value = filter.values[item.dataset.valueId];
        value.checked = !value.checked;
        const groupId = JSON.stringify(value.group_id);
        const group = filter.groups && filter.groups[groupId];
        if (group) {
            this._updateFilterGroupState(group);
        }
        this._notifyDomainUpdated();
    },
});

return SearchPanel;

});
