odoo.define('web.SearchPanel', function (require) {
"use strict";

/**
 * This file defines the SearchPanel widget for Kanban. It allows to
 * filter/manage data easily.
 */

const core = require('web.core');
const Domain = require('web.Domain');
const pyUtils = require('web.py_utils');
const viewUtils = require('web.viewUtils');
const Widget = require('web.Widget');

const qweb = core.qweb;

// defaultViewTypes is the list of view types for which the searchpanel is
// present by default (if not explicitly stated in the 'view_types' attribute
// in the arch)
const defaultViewTypes = ['kanban', 'tree'];

let nextId = 1;

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
    node.children.forEach((childNode, index) => {
        if (childNode.tag !== 'field') {
            return;
        }
        if (childNode.attrs.invisible === "1") {
            return;
        }
        const fieldName = childNode.attrs.name;
        const type = childNode.attrs.select === 'multi' ? 'filter' : 'category';

        const sectionId = `section_${nextId++}`;
        const section = {
            color: childNode.attrs.color,
            description: childNode.attrs.string || fields[fieldName].string,
            fieldName: fieldName,
            icon: childNode.attrs.icon,
            id: sectionId,
            index: index,
            type: type,
        };
        if (section.type === 'category') {
            section.icon = section.icon || 'fa-folder';
        } else if (section.type === 'filter') {
            section.disableCounters = !!pyUtils.py_eval(childNode.attrs.disable_counters || '0');
            section.domain = childNode.attrs.domain || '[]';
            section.groupBy = childNode.attrs.groupby;
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
        'click .o_search_panel_category_value .o_toggle_fold': '_onToggleFoldCategory',
        'click .o_search_panel_filter_group .o_toggle_fold': '_onToggleFoldFilterGroup',
        'change .o_search_panel_filter_value > div > input': '_onFilterValueChanged',
        'change .o_search_panel_filter_group > div > input': '_onFilterGroupChanged',
    },

    /**
     * @override
     * @param {Object} params
     * @param {Object} [params.defaultValues={}] the value(s) to activate by
     *   default, for each filter and category
     * @param {boolean} [params.defaultNoFilter=false] if true, select 'All' as
     *   value for each category that has no value specified in defaultValues
     *   (instead of looking in the localStorage for the last selected value)
     * @param {Object} params.fields
     * @param {string} params.model
     * @param {Array[]} params.searchDomain domain coming from controlPanel
     * @param {Object} params.sections
     * @param {Object} [params.state] state exported by another searchpanel
     *   instance
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);

        this.categories = {};
        this.filters = {};
        for (const section of Object.values(params.sections)) {
            const key = section.type === 'category'? 'categories'  : 'filters';
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
        this.searchDomain = params.searchDomain;
    },
    /**
     * @override
     */
    willStart: async function () {
        const _super = this._super;
        if (this.initialState) {
            this.filters = this.initialState.filters;
            this.categories = this.initialState.categories;
        } else {
            await this._fetchCategories();
            await this._fetchFilters();
            await this._applyDefaultFilterValues();
        }
        return _super.call(this, ...arguments);
    },
    /**
     * @override
     */
    start: function () {
        this._render();
        return this._super.apply(this, arguments);
    },
    /**
     * Called each time the searchPanel is attached into the DOM.
     */
    on_attach_callback: function () {
        if (this.scrollTop !== null) {
            this.el.scrollTop = this.scrollTop;
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

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
     * @params {Object} viewInfo the viewInfo of a search view
     * @params {string} viewInfo.arch
     * @params {Object} viewInfo.fields
     * @params {string} viewType the type of the current view (e.g. 'kanban')
     * @returns {Object|undefined}
     */
    computeSearchPanelParams: function (arch, fields, viewType) {
        var searchPanelSections;
        var classes;
        if (arch && fields) {
            viewType = viewType === 'list' ? 'tree' : viewType;
            arch  = viewUtils.parseArch(arch);
            const searchPanelNode = arch.children.find(child => child.tag === 'searchpanel');
            if (searchPanelNode) {
                var attrs = searchPanelNode.attrs;
                var viewTypes = defaultViewTypes;
                if (attrs.view_types) {
                    viewTypes = attrs.view_types.split(',');
                }
                if (attrs.class) {
                    classes = attrs.class.split(' ');
                }
                if (viewTypes.includes(viewType)) {
                    searchPanelSections = _processSearchPanelNode(searchPanelNode, fields);
                }
            }
        }
        return {
            sections: searchPanelSections,
            classes: classes,
        };
    },
    /**
     * Export the current state (categories and filters) of the searchpanel.
     *
     * @returns {Object}
     */
    exportState: function () {
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
    getDomain: function () {
        return this._getCategoryDomain().concat(this._getFilterDomain());
    },
    /**
     * Import a previously exported state (see exportState).
     *
     * @param {Object} state
     * @param {Object} state.filters.
     * @param {Object} state.categories
     */
    importState: function (state) {
        this.categories = state.categories || this.categories;
        this.filters = state.filters || this.filters;
        this.scrollTop = state.scrollTop;
        this._render();
    },
    /**
     * Reload the filters and re-render. Note that we only reload the filters if
     * the controlPanel domain or searchPanel domain has changed.
     *
     * @param {Object} params
     * @param {Array[]} params.searchDomain domain coming from controlPanel
     * @returns {Promise}
     */
    update: async function (params) {
        const currentSearchDomainStr = JSON.stringify(this.searchDomain);
        const newSearchDomainStr = JSON.stringify(params.searchDomain);
        if (this.needReload || (currentSearchDomainStr !== newSearchDomainStr)) {
            this.needReload = false;
            this.searchDomain = params.searchDomain;
            await this._fetchFilters();
        }
        return this._render();
    },


    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Set active values for each filter (coming from context). This needs to be
     * done only once, at widget startup.
     *
     * @private
     */
    _applyDefaultFilterValues: function () {
        Object.values(this.filters).forEach(filter => {
            const defaultValues = this.defaultValues[filter.fieldName] || [];
            defaultValues.forEach(function (value) {
                if (filter.values[value]) {
                    filter.values[value].checked = true;
                }
            });
            Object.values(filter.groups || []).forEach(group => {
                this._updateFilterGroupState(group);
            });
        });
    },
    /**
     * @private
     * @param {string} categoryId
     * @param {Object[]} values
     */
    _createCategoryTree: function (categoryId, values) {
        const category = this.categories[categoryId];
        const parentField = category.parentField;

        category.values = {};
        values.forEach(value => {
            category.values[value.id] = Object.assign({}, value, {
                childrenIds: [],
                folded: true,
                parentId: value[parentField] && value[parentField][0] || false,
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
     * @param {Object[]} values
     */
    _createFilterTree: function (filterId, values) {
        const filter = this.filters[filterId];

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
                const groupId = value.group_id;
                if (!groups[groupId]) {
                    if (groupId) {
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
            filter.sortedGroupIds = _.sortBy(groupIds, groupId => {
                return groups[groupId].sequence || groups[groupId].name;
            });
            Object.values(filter.groups).forEach(group => {
                Object.assign(filter.values, group.values);
            });
        } else {
            values.forEach(function (value) {
                filter.values[value.id] = value;
            });
            filter.sortedValueIds = values.map(value => value.id);
        }
    },
    /**
     * Fetch values for each category. This is done only once, at startup.
     *
     * @private
     * @returns {Promise} resolved when all categories have been fetched
     */
    _fetchCategories: function () {
        const proms = [];
        let prom;
        for (const category of Object.values(this.categories)) {
            const field = this.fields[category.fieldName];
            if (field.type === 'selection') {
                const values = field.selection.map(value => {
                    return {id: value[0], display_name: value[1]};
                });
                prom = Promise.resolve(values);
            } else {
                prom = this._rpc({
                    method: 'search_panel_select_range',
                    model: this.model,
                    args: [category.fieldName],
                }).then(result => {
                    category.parentField = result.parent_field;
                    return result.values;
                });
            }
            prom.then(values => {
                this._createCategoryTree(categoryId, values);
            });
            proms.push(prom);
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
    _fetchFilters: function () {
        const evalContext = {};
        for (const category of Object.values(this.categories)) {
            evalContext[category.fieldName] = category.activeValueId;
        }
        const categoryDomain = this._getCategoryDomain();
        const filterDomain = this._getFilterDomain();
        const proms = [];
        for (const filter of Object.values(this.filters)) {
            const prom = this._rpc({
                method: 'search_panel_select_multi_range',
                model: this.model,
                args: [filter.fieldName],
                kwargs: {
                    category_domain: categoryDomain,
                    comodel_domain: Domain.prototype.stringToArray(filter.domain, evalContext),
                    disable_counters: filter.disableCounters,
                    filter_domain: filterDomain,
                    group_by: filter.groupBy || false,
                    search_domain: this.searchDomain,
                },
            }).then(values => { this._createFilterTree(filter.id, values); });
            proms.push(prom);
        }
        return Promise.all(proms);
    },
    /**
     * @private
     * @param {Object} category
     * @param {Array} validValues
     * @returns id of the default item of the category or false
     */
    _getCategoryDefaultValue: function (category, validValues) {
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
     * @returns {Array[]}
     */
    _getCategoryDomain: function () {
        const domain = [];
        for (const category of Object.values(this.categories)) {
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
     * @param {string} filterId
     * @returns {Array[]}
     */
    _getFilterDomain: function (filterId) {
        const domain = [];

        function addCondition(fieldName, checkedValues) {
            if (checkedValues.length) {
                const ids = checkedValues.map(v => v.id);
                domain.push([fieldName, 'in', ids]);
            }
        }

        for (const filter of Object.values(this.filters)) {
            if (filter.id === filterId) {
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
     * The active id of each category is stored in the localStorage, s.t. it
     * can be restored afterwards (when the action is reloaded, for instance).
     * This function returns the key in the sessionStorage for a given category.
     *
     * @param {Object} category
     * @returns {string}
     */
    _getLocalStorageKey: function (category) {
        return 'searchpanel_' + this.model + '_' + category.fieldName;
    },
    /**
     * @private
     * @param {Object} category
     * @param {integer} categoryValueId
     * @returns {integer[]} list of ids of the ancestors of the given value in
     *   the given category
     */
    _getAncestorValueIds: function (category, categoryValueId) {
        const { parentId }  = category.values[categoryValueId];
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
    _notifyDomainUpdated: function () {
        this.needReload = true;
        this.trigger_up('search_panel_domain_updated', {
            domain: this.getDomain(),
        });
    },
    /**
     * @private
     */
    _render: function () {
        this.$el.empty();

        // sort categories and filters according to their index
        const categories = Object.values(this.categories);
        const filters = Object.values(this.filters);
        const sections = categories.concat(filters).sort(function (s1, s2) {
            return s1.index - s2.index;
        });

        sections.forEach(section => {
            if (Object.keys(section.values).length) {
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
    _renderCategory: function (category) {
        return qweb.render('SearchPanel.Category', {category: category});
    },
    /**
     * @private
     * @param {Object} filter
     * @returns {jQuery}
     */
    _renderFilter: function (filter) {
        const $filter = $(qweb.render('SearchPanel.Filter', {filter: filter}));

        // set group inputs in indeterminate state when necessary
        Object.keys(filter.groups || {}).forEach(groupId => {
            const group = filter.groups[groupId];
            const { state } = group;
            // group 'false' is not displayed
            if (groupId !== 'false' && state === 'indeterminate') {
                $filter
                    .find(`.o_search_panel_filter_group[data-group-id="${groupId}"] input`)
                    .get(0)
                    .indeterminate = true;
            }
        });

        return $filter;
    },
    /**
     * Updates the state property of a given filter's group according to the
     * checked property of its values.
     *
     * @private
     * @param {Object} group
     */
    _updateFilterGroupState: function (group) {
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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onCategoryValueClicked: function (ev) {
        ev.stopPropagation();
        const $item = $(ev.currentTarget).closest('.o_search_panel_category_value');
        const category = this.categories[$item.data('categoryId')];
        const valueId = $item.data('id') || false;
        category.activeValueId = valueId;
        if (category.values[valueId]) {
            category.values[valueId].folded = !category.values[valueId].folded;
        }
        const storageKey = this._getLocalStorageKey(category);
        this.call('local_storage', 'setItem', storageKey, valueId);
        this._notifyDomainUpdated();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onFilterGroupChanged: function (ev) {
        ev.stopPropagation();
        const $item = $(ev.target).closest('.o_search_panel_filter_group');
        const filter = this.filters[$item.data('filterId')];
        const groupId = $item.data('groupId');
        const group = filter.groups[groupId];
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
    _onFilterValueChanged: function (ev) {
        ev.stopPropagation();
        const $item = $(ev.target).closest('.o_search_panel_filter_value');
        const valueId = $item.data('valueId');
        const filter = this.filters[$item.data('filterId')];
        const value = filter.values[valueId];
        value.checked = !value.checked;
        const group = filter.groups && filter.groups[value.group_id];
        if (group) {
            this._updateFilterGroupState(group);
        }
        this._notifyDomainUpdated();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onToggleFoldCategory: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const $item = $(ev.currentTarget).closest('.o_search_panel_category_value');
        const category = this.categories[$item.data('categoryId')];
        const valueId = $item.data('id');
        category.values[valueId].folded = !category.values[valueId].folded;
        this._render();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onToggleFoldFilterGroup: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const $item = $(ev.currentTarget).closest('.o_search_panel_filter_group');
        const filter = this.filters[$item.data('filterId')];
        const groupId = $item.data('groupId');
        filter.groups[groupId].folded = !filter.groups[groupId].folded;
        this._render();
    },
});

return SearchPanel;

});
