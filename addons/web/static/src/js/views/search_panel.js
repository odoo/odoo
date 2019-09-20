odoo.define('web.SearchPanel', function (require) {
"use strict";

/**
 * This file defines the SearchPanel widget for Kanban. It allows to
 * filter/manage data easily.
 */

var core = require('web.core');
var Domain = require('web.Domain');
var pyUtils = require('web.py_utils');
var viewUtils = require('web.viewUtils');
var Widget = require('web.Widget');

var qweb = core.qweb;

// defaultViewTypes is the list of view types for which the searchpanel is
// present by default (if not explicitly stated in the 'view_types' attribute
// in the arch)
var defaultViewTypes = ['kanban', 'tree'];

/**
 * Given a <searchpanel> arch node, iterate over its children to generate the
 * description of each section (being either a category or a filter).
 *
 * @param {Object} node a <searchpanel> arch node
 * @param {Object} fields the fields of the model
 * @returns {Object}
 */
function _processSearchPanelNode(node, fields) {
    var sections = {};
    node.children.forEach((childNode, index) => {
        if (childNode.tag !== 'field') {
            return;
        }
        if (childNode.attrs.invisible === "1") {
            return;
        }
        var fieldName = childNode.attrs.name;
        var type = childNode.attrs.select === 'multi' ? 'filter' : 'category';

        var sectionId = _.uniqueId('section_');
        var section = {
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

var SearchPanel = Widget.extend({
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

        this.categories = _.pick(params.sections, function (section) {
            return section.type === 'category';
        });
        this.filters = _.pick(params.sections, function (section) {
            return section.type === 'filter';
        });

        this.initialState = params.state;
        this.scrollTop = this.initialState && this.initialState.scrollTop || null;
        this.defaultValues = params.defaultValues || {};
        if (params.defaultNoFilter) {
            Object.keys(this.categories).forEach((categoryId) => {
                var fieldName = this.categories[categoryId].fieldName;
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
    willStart: function () {
        var self = this;
        var loadCategoriesProm;
        if (this.initialState) {
            this.filters = this.initialState.filters;
            this.categories = this.initialState.categories;
        } else {
            loadCategoriesProm = this._fetchCategories().then(function () {
                return self._fetchFilters().then(self._applyDefaultFilterValues.bind(self));
            });
        }
        return Promise.all([loadCategoriesProm, this._super.apply(this, arguments)]);
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
    computeSearchPanelParams: function (viewInfo, viewType) {
        var searchPanelSections;
        var classes;
        if (viewInfo) {
            var arch = viewUtils.parseArch(viewInfo.arch);
            viewType = viewType === 'list' ? 'tree' : viewType;
            arch.children.forEach(function (node) {
                if (node.tag === 'searchpanel') {
                    var attrs = node.attrs;
                    var viewTypes = defaultViewTypes;
                    if (attrs.view_types) {
                        viewTypes = attrs.view_types.split(',');
                    }
                    if (attrs.class) {
                        classes = attrs.class.split(' ');
                    }
                    if (viewTypes.indexOf(viewType) !== -1) {
                        searchPanelSections = _processSearchPanelNode(node, viewInfo.fields);
                    }
                }
            });
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
    update: function (params) {
        var currentSearchDomainStr = JSON.stringify(this.searchDomain);
        var newSearchDomainStr = JSON.stringify(params.searchDomain);
        var filtersProm;
        if (this.needReload || (currentSearchDomainStr !== newSearchDomainStr)) {
            this.needReload = false;
            this.searchDomain = params.searchDomain;
            filtersProm = this._fetchFilters();
        }
        return Promise.resolve(filtersProm).then(this._render.bind(this));
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
        var self = this;
        Object.keys(this.filters).forEach(function (filterId) {
            var filter = self.filters[filterId];
            var defaultValues = self.defaultValues[filter.fieldName] || [];
            defaultValues.forEach(function (value) {
                if (filter.values[value]) {
                    filter.values[value].checked = true;
                }
            });
            Object.keys(filter.groups || []).forEach(function (groupId) {
                self._updateFilterGroupState(filter.groups[groupId]);
            });
        });
    },
    /**
     * @private
     * @param {string} categoryId
     * @param {Object[]} values
     */
    _createCategoryTree: function (categoryId, values) {
        var category = this.categories[categoryId];
        var parentField = category.parentField;

        category.values = {};
        _.each(values, function (value) {
            category.values[value.id] = _.extend({}, value, {
                childrenIds: [],
                folded: true,
                parentId: value[parentField] && value[parentField][0] || false,
            });
        });
        _.map(values, function (value) {
            var value = category.values[value.id];
            var parentCategoryId = value.parentId;
            if (parentCategoryId && parentCategoryId in category.values) {
                category.values[parentCategoryId].childrenIds.push(value.id);
            }
        });
        category.rootIds = _.filter(_.map(values, function (value) {
            return value.id;
        }), function (valueId) {
            var value = category.values[valueId];
            return value.parentId === false;
        });

        // set active value
        var validValues = _.pluck(category.values, 'id').concat([false]);
        var value = this._getCategoryDefaultValue(category, validValues);
        category.activeValueId = _.contains(validValues, value) ? value : false;

        // unfold ancestor values of active value to make it is visible
        if (category.activeValueId) {
            var parentValueIds = this._getAncestorValueIds(category, category.activeValueId);
            parentValueIds.forEach(function (parentValue) {
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
        var filter = this.filters[filterId];

        // restore checked property
        values.forEach(function (value) {
            var oldValue = filter.values && filter.values[value.id];
            value.checked = oldValue && oldValue.checked || false;
        });

        filter.values = {};
        var groupIds = [];
        if (filter.groupBy) {
            var groups = {};
            values.forEach(function (value) {
                var groupId = value.group_id;
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
                    var oldGroup = filter.groups && filter.groups[groupId];
                    groups[groupId].state = oldGroup && oldGroup.state || false;
                    groups[groupId].folded = oldGroup && oldGroup.folded || false;
                }
                groups[groupId].values[value.id] = value;
                groups[groupId].sortedValueIds.push(value.id);
            });
            filter.groups = groups;
            filter.sortedGroupIds = _.sortBy(groupIds, function (groupId) {
                return groups[groupId].sequence || groups[groupId].name;
            });
            Object.keys(filter.groups).forEach(function (groupId) {
                filter.values = _.extend(filter.values, filter.groups[groupId].values);
            });
        } else {
            values.forEach(function (value) {
                filter.values[value.id] = value;
            });
            filter.sortedValueIds = values.map(function (value) {
                return value.id;
            });
        }
    },
    /**
     * Fetch values for each category. This is done only once, at startup.
     *
     * @private
     * @returns {Promise} resolved when all categories have been fetched
     */
    _fetchCategories: function () {
        var self = this;
        var proms = Object.keys(this.categories).map(function (categoryId) {
            var category = self.categories[categoryId];
            var field = self.fields[category.fieldName];
            var categoriesProm;
            if (field.type === 'selection') {
                var values = field.selection.map(function (value) {
                    return {id: value[0], display_name: value[1]};
                });
                categoriesProm = Promise.resolve(values);
            } else {
                categoriesProm = self._rpc({
                    method: 'search_panel_select_range',
                    model: self.model,
                    args: [category.fieldName],
                }).then(function (result) {
                    category.parentField = result.parent_field;
                    return result.values;
                });
            }
            return categoriesProm.then(function (values) {
                self._createCategoryTree(categoryId, values);
            });
        });
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
        var self = this;
        var evalContext = {};
        Object.keys(this.categories).forEach(function (categoryId) {
            var category = self.categories[categoryId];
            evalContext[category.fieldName] = category.activeValueId;
        });
        var categoryDomain = this._getCategoryDomain();
        var filterDomain = this._getFilterDomain();
        var proms = Object.keys(this.filters).map(function (filterId) {
            var filter = self.filters[filterId];
            return self._rpc({
                method: 'search_panel_select_multi_range',
                model: self.model,
                args: [filter.fieldName],
                kwargs: {
                    category_domain: categoryDomain,
                    comodel_domain: Domain.prototype.stringToArray(filter.domain, evalContext),
                    disable_counters: filter.disableCounters,
                    filter_domain: filterDomain,
                    group_by: filter.groupBy || false,
                    search_domain: self.searchDomain,
                },
            }).then(function (values) {
                self._createFilterTree(filterId, values);
            });
        });
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
        var value = this.defaultValues[category.fieldName];
        // if not set in context, or set to an unknown value, set active value
        // from localStorage
        if (!_.contains(validValues, value)) {
            var storageKey = this._getLocalStorageKey(category);
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
        var self = this;

        function categoryToDomain(domain, categoryId) {
            var category = self.categories[categoryId];
            if (category.activeValueId) {
                var field = self.fields[category.fieldName];
                var op = (field.type === 'many2one' && category.parentField) ? 'child_of' : '=';
                domain.push([category.fieldName, op, category.activeValueId]);
            }
            return domain;
        }

        return Object.keys(this.categories).reduce(categoryToDomain, []);
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
     * @returns {Array[]}
     */
    _getFilterDomain: function () {
        var self = this;

        function getCheckedValueIds(values) {
            return Object.keys(values).reduce(function (checkedValues, valueId) {
                if (values[valueId].checked) {
                    checkedValues.push(values[valueId].id);
                }
                return checkedValues;
            }, []);
        }

        function filterToDomain(domain, filterId) {
            var filter = self.filters[filterId];
            if (filter.groups) {
                Object.keys(filter.groups).forEach(function (groupId) {
                    var group = filter.groups[groupId];
                    var checkedValues = getCheckedValueIds(group.values);
                    if (checkedValues.length) {
                        domain.push([filter.fieldName, 'in', checkedValues]);
                    }
                });
            } else if (filter.values) {
                var checkedValues = getCheckedValueIds(filter.values);
                if (checkedValues.length) {
                    domain.push([filter.fieldName, 'in', checkedValues]);
                }
            }
            return domain;
        }

        return Object.keys(this.filters).reduce(filterToDomain, []);
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
        var categoryValue = category.values[categoryValueId];
        var parentId = categoryValue.parentId;
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
        var self = this;
        this.$el.empty();

        // sort categories and filters according to their index
        var categories = Object.keys(this.categories).map(function (categoryId) {
            return self.categories[categoryId];
        });
        var filters = Object.keys(this.filters).map(function (filterId) {
            return self.filters[filterId];
        });
        var sections = categories.concat(filters).sort(function (s1, s2) {
            return s1.index - s2.index;
        });

        sections.forEach(function (section) {
            if (Object.keys(section.values).length) {
                if (section.type === 'category') {
                    self.$el.append(self._renderCategory(section));
                } else {
                    self.$el.append(self._renderFilter(section));
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
        var $filter = $(qweb.render('SearchPanel.Filter', {filter: filter}));

        // set group inputs in indeterminate state when necessary
        Object.keys(filter.groups || {}).forEach(function (groupId) {
            var state = filter.groups[groupId].state;
            // group 'false' is not displayed
            if (groupId !== 'false' && state === 'indeterminate') {
                $filter
                    .find('.o_search_panel_filter_group[data-group-id=' + groupId + '] input')
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
        var valuePartition = _.partition(Object.keys(group.values), function (valueId) {
            return group.values[valueId].checked;
        });
        if (valuePartition[0].length && valuePartition[1].length) {
            group.state = 'indeterminate';
        } else if (valuePartition[0].length) {
            group.state = 'checked';
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
        var $item = $(ev.currentTarget).closest('.o_search_panel_category_value');
        var category = this.categories[$item.data('categoryId')];
        var valueId = $item.data('id') || false;
        category.activeValueId = valueId;
        if (category.values[valueId]) {
            category.values[valueId].folded = !category.values[valueId].folded;
        }
        var storageKey = this._getLocalStorageKey(category);
        this.call('local_storage', 'setItem', storageKey, valueId);
        this._notifyDomainUpdated();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onFilterGroupChanged: function (ev) {
        ev.stopPropagation();
        var $item = $(ev.target).closest('.o_search_panel_filter_group');
        var filter = this.filters[$item.data('filterId')];
        var groupId = $item.data('groupId');
        var group = filter.groups[groupId];
        group.state = group.state === 'checked' ? 'unchecked' : 'checked';
        Object.keys(group.values).forEach(function (valueId) {
            group.values[valueId].checked = group.state === 'checked';
        });
        this._notifyDomainUpdated();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onFilterValueChanged: function (ev) {
        ev.stopPropagation();
        var $item = $(ev.target).closest('.o_search_panel_filter_value');
        var valueId = $item.data('valueId');
        var filter = this.filters[$item.data('filterId')];
        var value = filter.values[valueId];
        value.checked = !value.checked;
        var group = filter.groups && filter.groups[value.group_id];
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
        var $item = $(ev.currentTarget).closest('.o_search_panel_category_value');
        var category = this.categories[$item.data('categoryId')];
        var valueId = $item.data('id');
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
        var $item = $(ev.currentTarget).closest('.o_search_panel_filter_group');
        var filter = this.filters[$item.data('filterId')];
        var groupId = $item.data('groupId');
        filter.groups[groupId].folded = !filter.groups[groupId].folded;
        this._render();
    },
});

return SearchPanel;

});
