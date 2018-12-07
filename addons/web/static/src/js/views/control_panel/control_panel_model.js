odoo.define('web.ControlPanelModel', function (require) {
"use strict";

var controlPanelViewParameters = require('web.controlPanelViewParameters');
var core = require('web.core');
var Domain = require('web.Domain');
var mvc = require('web.mvc');
var pyUtils = require('web.py_utils');
var searchBarAutocompleteRegistry = require('web.search_bar_autocomplete_sources_registry');
var session = require('web.session');

var _t = core._t;

var DEFAULT_TIMERANGE = controlPanelViewParameters.DEFAULT_TIMERANGE;
var TIME_RANGE_OPTIONS = controlPanelViewParameters.TIME_RANGE_OPTIONS;
var COMPARISON_TIME_RANGE_OPTIONS = controlPanelViewParameters.COMPARISON_TIME_RANGE_OPTIONS;

var ControlPanelModel = mvc.Model.extend({
    /**
     * @override
     * @param {string} [params.actionId]
     * @param {string} [params.context={}]
     * @param {string} [params.domain=[]]
     * @param {string} [params.field={}]
     * @param {string} [params.modelName]
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);

        // Tricks to avoid losing information on filter descriptions in control panel model configuration
        TIME_RANGE_OPTIONS = TIME_RANGE_OPTIONS.map(function (option) {
            return _.extend(option, {description: option.description.toString()});
        });
        COMPARISON_TIME_RANGE_OPTIONS = COMPARISON_TIME_RANGE_OPTIONS.map(function (option) {
            return _.extend(option, {description: option.description.toString()});
        });


        this.modelName = params.modelName;
        // info on fields of model this.modelName
        this.fields = params.fields || {};

        // info on current action
        this.actionId = params.actionId;
        this.actionContext = params.context || {};
        this.actionDomain = params.domain || [];

        // triple determining a control panel model configuration
        this.filters = {};
        this.groups = {};
        this.query = [];
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Activate a given filter of type 'timeRange' with a timeRangeId
     * and optionaly a comparsionTimeRangeId
     *
     * @param {string} filterId
     * @param {string} timeRangeId
     * @param {string} [comparisonTimeRangeId]
     */
    activateTimeRange: function (filterId, timeRangeId, comparisonTimeRangeId) {
        var filter = this.filters[filterId];
        filter.timeRangeId = timeRangeId || filter.defaultTimeRangeId;
        filter.comparisonTimeRangeId = comparisonTimeRangeId;
        var group = this.groups[filter.groupId];
        var groupActive = group.activeFilterIds.length;
        if (groupActive) {
            group.activeFilterIds = [filterId];
        } else {
            this.toggleFilter(filterId);
        }
    },
    /**
     * Ccreate an ir_filter server side. If the operation is successful, a new
     * filter of type 'favorite' is created and activated.
     *
     * @param {Object} newFavorite
     */
    createNewFavorite: function (newFavorite) {
        return this._saveQuery(_.pick(
            newFavorite,
            ['description', 'isDefault', 'isShared', 'type']
        )).then(function () {
            newFavorite.on_success();
        });
    },
    /**
     * Create new filters of type 'filter' with same new groupId and groupNumber.
     * They are activated.
     *
     * @param {Object[]} newFilters
     * @returns {string[]} filterIds, ids of the newly created filters
     */
    createNewFilters: function (newFilters) {
        var self = this;
        var filterIds = [];
        var groupNumber = this._generateNewGroupNumber();
        this._createGroupOfFilters(newFilters);
        newFilters.forEach(function (filter) {
            filter.groupNumber = groupNumber;
            self.toggleFilter(filter.id);
            filterIds.push(filter.id);
        });
        return filterIds;
    },
    /**
     * Create a new groupBy with the groupId shared by all filters of type 'groupBy'
     * but a new groupNumber
     * It is activated.
     *
     * @param {Object} newGroupBy
     */
    createNewGroupBy: function (newGroupBy) {
        var id = _.uniqueId('__filter__');
        newGroupBy.id = id;
        newGroupBy.groupId = this._getGroupIdOfType('groupBy');
        newGroupBy.groupNumber = this._generateNewGroupNumber();
        this.filters[id] = newGroupBy;
        if (_.contains(['date', 'datetime'], newGroupBy.fieldType)) {
            this.toggleFilterWithOptions(newGroupBy.id);
        } else {
            this.toggleFilter(newGroupBy.id);
        }
    },
    /**
     * Ensure that the filters determined by the given filterIds are
     * deactivated (if one or many of them are already deactivated, nothing bad happens)
     *
     * @param {string[]} filterIds
     */
    deactivateFilters: function (filterIds) {
        var self = this;
        filterIds.forEach(function (filterId) {
            var filter = self.filters[filterId];
            var group = self.groups[filter.groupId];
            if (_.contains(group.activeFilterIds, filterId)) {
                self.toggleFilter(filterId);
            }
        });
    },
    /**
     * Deactivate all filters in a given group with given id.
     *
     * @param {string} groupId
     */
    deactivateGroup: function (groupId) {
        var self = this;
        var group = this.groups[groupId];
        _.each(group.activeFilterIds, function (filterId) {
            var filter = self.filters[filterId];
            // TODO: put this logic in toggleFilter 'field' type
            if (filter.autoCompleteValues) {
                filter.autoCompleteValues = [];
            }
        });
        // TODO: use toggleFilter here
        group.activeFilterIds = [];
        this.query.splice(this.query.indexOf(groupId), 1);
    },
    /**
     * Delete a filter of type 'favorite' with given filterId server side and in control panel model.
     * Of course this forces the filter to be removed from the search query.
     *
     * @param {string} filterId
     */
    deleteFilterEverywhere: function (filterId) {
        var self = this;
        var filter = this.filters[filterId];
        var def = this.deleteFilter(filter.serverSideId).then(function () {
            var activeFavoriteId = self.groups[filter.groupId].activeFilterIds[0];
            var isActive = activeFavoriteId === filterId;
            if (isActive) {
                self.toggleFilter(filterId);
            }
            delete self.filters[filterId];
        });
        return def;
    },
    /**
     * Return the state of the control panel (the filters, groups and the
     * current query). This state can then be used in an other control panel
     * model (with same key modelName) via the importState method.
     *
     * @returns {Object}
     */
    exportState: function () {
        return {
            filters: this.filters,
            groups: this.groups,
            query: this.query,
        };
    },
    /**
     * @override
     *
     * @returns {Object}
     */
    get: function () {
        var self = this;
        // we maintain a unique source activeFilterIds that contain information
        // on active filters. But the renderer can have more information since
        // it does not modifies filters activity.
        // We thus give a different structure to renderer that may contain duplicated
        // information.
        // Note that filters are filters of filter type only, groupbys are groupbys,...!
        var filterFields = [];
        var filters = [];
        var groupBys = [];
        var timeRanges = [];
        var favorites = [];
        Object.keys(this.filters).forEach(function (filterId) {
            var filter = _.extend({}, self.filters[filterId]);
            var group = self.groups[filter.groupId];
            filter.isActive = group.activeFilterIds.indexOf(filterId) !== -1;
            if (filter.type === 'field') {
                filterFields.push(filter);
            }
            if (filter.type === 'filter') {
                filters.push(filter);
            }
            if (filter.type === 'groupBy') {
                groupBys.push(filter);
            }
            if (filter.type === 'favorite') {
                favorites.push(filter);
            }
            if (filter.type === 'timeRange') {
                timeRanges.push(filter);
            }
        });
        var facets = [];
        // resolve active filters for facets
        this.query.forEach(function (groupID) {
            var group = self.groups[groupID];
            var facet = _.extend({}, group);
            facet.filters = facet.activeFilterIds.map(function (filterID) {
                return self.filters[filterID];
            });
            facets.push(facet);
        });
        favorites = _.sortBy(favorites, 'groupNumber');
        return {
            facets: facets,
            filterFields: filterFields,
            filters: filters,
            groupBys: groupBys,
            timeRanges: timeRanges,
            favorites: favorites,
            groups: this.groups,
            query: _.extend([], this.query),
            fields: this.fields,
        };
    },
    /**
     * @returns {Object} An object called search query with keys domain, groupBy,
     *                   context, orderedBy.
     */
    getQuery: function () {
        var userContext = session.user_context;
        var context = _.extend(
            pyUtils.eval('contexts', this._getQueryContext(), userContext),
            this._getTimeRangeMenuData(true)
        );
        var domain = Domain.prototype.stringToArray(this._getDomain(), userContext);
        // this must be done because pyUtils.eval does not know that it needs to evaluate domains within contexts
        if (context.timeRangeMenuData) {
            if (typeof context.timeRangeMenuData.timeRange === 'string') {
                context.timeRangeMenuData.timeRange = pyUtils.eval('domain', context.timeRangeMenuData.timeRange);
            }
            if (typeof context.timeRangeMenuData.comparisonTimeRange === 'string') {
                context.timeRangeMenuData.comparisonTimeRange = pyUtils.eval('domain', context.timeRangeMenuData.comparisonTimeRange);
            }
        }
        var action_context = this.actionContext;
        var results = pyUtils.eval_domains_and_contexts({
            domains: [this.actionDomain].concat([domain] || []),
            contexts: [action_context].concat(context || []),
            eval_context: session.user_context,
        });
        if (results.error) {
            throw new Error(_.str.sprintf(_t("Failed to evaluate search criterions")+": \n%s",
                            JSON.stringify(results.error)));
        }

        var groupBys = this._getGroupBy();
        var groupBy = groupBys.length ?
                        groupBys :
                        (this.actionContext.group_by || []);
        groupBy = (typeof groupBy === 'string') ? [groupBy] : groupBy;

        context = _.omit(results.context, 'time_ranges');

        return {
            context: context,
            domain: results.domain,
            groupBy: groupBy,
            orderedBy: this._getOrderedBy(),
        };
    },
    /**
     * Set filters, groups, and query keys according to the given state.
     *
     * @param {Object} state
     */
    importState: function (state) {
        this.filters = state.filters;
        this.groups = state.groups;
        this.query = state.query;
    },
    /**
     * The load method is the place where the favorites are also loaded and
     * the model state is first established.
     * The computation of the active filters at initialization is accomplished
     * here.
     *
     * @param {Object} params
     * @param {boolean} [params.activateDefaultFavorite=false]
     * @param {Array[]} [params.groups=[]]
     * @param {Object} [params.initialState]
     * @param {string[]} [params.searchMenuTypes=[]]
     * @param {Object} [params.timeRanges]
     * @param {boolean} [params.withSearchBar]
     * @returns {Deferred}
     */
    load: function (params) {
        var self = this;
        this.searchMenuTypes = params.searchMenuTypes || [];
        this.activateDefaultFavorite = params.activateDefaultFavorite;

        if (!params.withSearchBar && params.searchMenuTypes.length === 0) {
            // The model state will remain as set in init method
            // and the info comming from arch put in params.groups (if any)
            // will be lost. This is not a problem because the state
            // won't be use elsewhere.
            return $.when();
        }
        if (params.initialState) {
            this.importState(params.initialState);
            return $.when();
        } else {
            var groups = params.groups || [];
            groups.forEach(function (group) {
                self._createGroupOfFilters(group);
            });
            if (this._getGroupIdOfType('groupBy') === undefined) {
                this._createEmptyGroup('groupBy');
            }
            this._createGroupOfTimeRanges();
            return $.when.apply($, self._loadSearchDefaults()).then(function () {
                return self._loadFavorites().then(function () {
                    if (self.query.length === 0) {
                        self._activateDefaultFilters();
                        self._activateDefaultTimeRanges(params.timeRanges);
                    }
                });
            });
        }
    },
    /**
     * Toggle a filter with given id in a way appropriate to its type.
     *
     * @param {Object} params
     * @param {string} params.filterId
     * @param {Object} params.autoCompleteValues
     */
    toggleAutoCompletionFilter: function (params) {
        var filter = this.filters[params.filterId];
        if (filter.type === 'field') {
            filter.autoCompleteValues = params.autoCompleteValues;
            // the autocompletion filter is dynamic
            filter.domain = this._getAutoCompletionFilterDomain(filter);
            // active the filter
            var group = this.groups[filter.groupId];
            if (!group.activeFilterIds.includes(filter.id)) {
                group.activeFilterIds.push(filter.id);
                this.query.push(group.id);
            }
        } else {
            if (filter.hasOptions) {
                this.toggleFilterWithOptions(filter.id);
            } else {
                this.toggleFilter(filter.id);
            }
        }
    },
    /**
     * Toggle a filter throught the modification of this.groups and potentially
     * of this.query and this.filters.
     *
     * @param {string} filterId
     */
    toggleFilter: function (filterId) {
        var self = this;
        var filter = this.filters[filterId];
        var group = this.groups[filter.groupId];
        var index = group.activeFilterIds.indexOf(filterId);
        var initiaLength = group.activeFilterIds.length;
        if (index === -1) {
            // we need to deactivate all groups when activating a favorite
            if (filter.type === 'favorite') {
                this.query.forEach(function (groupId) {
                    self.groups[groupId].activeFilterIds = [];
                });
                this.query = [];
            }
            group.activeFilterIds.push(filterId);
            // if initiaLength is 0, the group was not active.
            if (filter.type === 'favorite' || initiaLength === 0) {
                this.query.push(group.id);
            }
        } else {
            if (filter.type === 'field' && filter.autoCompleteValues) {
                filter.autoCompleteValues = [];
            }
            group.activeFilterIds.splice(index, 1);
            // if initiaLength is 1, the group is now inactive.
            if (initiaLength === 1) {
                this.query.splice(this.query.indexOf(group.id), 1);
            }
        }
    },
    /**
     * Used to toggle a given filter(Id) that has options with a given option(Id).
     *
     * @param {string} filterId
     * @param {string} [optionId]
     */
    toggleFilterWithOptions: function (filterId, optionId) {
        var filter = this.filters[filterId];
        var group = this.groups[filter.groupId];
        var alreadyActive = group.activeFilterIds.indexOf(filterId) !== -1;
        if (alreadyActive) {
            if (filter.currentOptionId === optionId) {
                this.toggleFilter(filterId);
                filter.currentOptionId = false;
            } else {
                filter.currentOptionId = optionId || filter.defaultOptionId;
            }
        } else {
            this.toggleFilter(filterId);
            filter.currentOptionId = optionId || filter.defaultOptionId;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Activate all filters (but favorites) with key isDefault=true
     *
     * @private
     */
    _activateDefaultFilters: function () {
        var self = this;
        Object.keys(this.filters).forEach(function (filterId) {
            var filter = self.filters[filterId];
            // if we are here, this means there is no favorite with isDefault set to true
            if (filter.isDefault && filter.type !== 'favorite') {
                if (filter.hasOptions) {
                    self.toggleFilterWithOptions(filter.id);
                } else {
                    self.toggleFilter(filter.id);
                }
        }});
    },
    /**
     * If defaultTimeRanges param is provided, activate the filter of type
     * 'timeRange' it determines with the correct options.
     *
     * @private
     * @param {Object} [defaultTimeRanges]
     * @param {string} [defaultTimeRanges.field], field of type 'date' or 'datetime'
     * @param {string} [defaultTimeRanges.range], to choose among the following:
     *  'last_7_days', 'last_30_days', 'last_365_days', 'today', 'this_week',
     *  'this_month', 'this_quarter', 'this_year', 'yesterday', 'last_week',
     *  'last_month', 'last_quarter', 'last_year'
     * @param {'previous_period'|'previous_year'} [defaultTimeRanges.comparisonRange]
     */
    _activateDefaultTimeRanges: function (defaultTimeRanges) {
        var self = this;
        if (defaultTimeRanges) {
            var filterId = Object.keys(this.filters).find(function (filterId) {
                var filter = self.filters[filterId];
                return filter.type === 'timeRange' && filter.fieldName === defaultTimeRanges.field;
            });
            if (filterId) {
                this.activateTimeRange(
                    filterId,
                    defaultTimeRanges.range,
                    defaultTimeRanges.comparisonRange
                );
            }
        }
    },
    /**
     * Create a new filter of type 'favorite' and toggle it.
     * It belongs to the unique group of favorites.
     *
     * @private
     * @param {Object} favorite
     */
    _addNewFavorite: function (favorite) {
        var id = _.uniqueId('__filter__');
        favorite.id = id;
        favorite.groupId = this._getGroupIdOfType('favorite');
        this.filters[id] = favorite;
        this.toggleFilter(favorite.id);
    },
    /**
     * Add a new empty group to this.groups of a specified type.
     *
     * @private
     * @param {string} type
     */
    _createEmptyGroup: function (type) {
        var id = _.uniqueId('__group__');
        this.groups[id] = {
            id: id,
            type: type,
            activeFilterIds: [],
        };
    },
    /**
     * Using a list of 'prefilters', create a new group in this.groups and a new
     * filter for each prefilter. The new filters are put in the new group.
     *
     * @private
     * @param {Object[]} group, list of 'prefilters'
     */
    _createGroupOfFilters: function (group) {
        var self= this;
        var type;
        var groupId = _.uniqueId('__group__');
        group.forEach(function (filter) {
            var id = _.uniqueId('__filter__');
            filter.id = id;
            filter.groupId = groupId;
            type = filter.type;
            self.filters[id] = filter;
        });
        this.groups[groupId] = {
            id: groupId,
            type: type,
            activeFilterIds: [],
        };
    },
    /**
     * Add a group of type 'timeRange' in this.groups and generate a filter
     * of the same type for each suitable field in this.fields. The new filters
     * are put in the new group.
     *
     * @private
     */
    _createGroupOfTimeRanges: function () {
        var self = this;
        var timeRanges = [];
        Object.keys(this.fields).forEach(function (fieldName) {
            var field = self.fields[fieldName];
            var fieldType = field.type;
            if (_.contains(['date', 'datetime'], fieldType) && field.sortable) {
                timeRanges.push({
                    type: 'timeRange',
                    description: field.string,
                    fieldName : fieldName,
                    fieldType: fieldType,
                    timeRangeId: false,
                    comparisonTimeRangeId: false,
                    defaultTimeRangeId: DEFAULT_TIMERANGE,
                    timeRangeOptions: TIME_RANGE_OPTIONS,
                    comparisonTimeRangeOptions: COMPARISON_TIME_RANGE_OPTIONS
                });
            }
        });
        if (timeRanges.length) {
            this._createGroupOfFilters(timeRanges);
        } else {
            // create empty timeRange group
            this._createEmptyGroup('timeRange');
        }
    },
    /**
     * Create a new groupNumber not already used elsewhere.
     * Group numbers are used to separate graphically groups of items  in the
     * search menus (filter menu, groupBy menu,...).
     *
     * @private
     * @returns {number} groupNumber
     */
    _generateNewGroupNumber: function () {
        var self = this;
        var groupNumber = 1 + Object.keys(this.filters).reduce(
            function (max, filterId) {
                var filter = self.filters[filterId];
                if (filter.groupNumber) {
                    max = Math.max(filter.groupNumber, max);
                }
                return max;
            },
            1
        );
        return groupNumber;
    },
    /**
     * @private
     * @param {Object} filter
     * @returns {string} domain
     */
    _getAutoCompletionFilterDomain: function (filter) {
        var domain = "";
        var field = this.fields[filter.attrs.name];
        // TODO: should not do that, the domain logic should be put somewhere else
        var Obj = searchBarAutocompleteRegistry.getAny([filter.attrs.widget, field.type]);
        if (Obj) {
            var obj = new (Obj) (this, filter, field, this.actionContext);
            domain = obj.getDomain(filter.autoCompleteValues);
        }
        return domain;
    },
    /**
     * Return the string representation of a domain created by combining
     * appropriately (with an 'AND') the domains coming from the active groups.
     *
     * @private
     * @returns {string} the string representation of a domain
     */
    _getDomain: function () {
        var self = this;
        var domains = this.query.map(function (groupId) {
            var group = self.groups[groupId];
            return self._getGroupDomain(group);
        });
        return pyUtils.assembleDomains(domains, 'AND');
    },
    /**
     * Return the context of the provided filter.
     *
     * @private
     * @param {Object} filter
     * @returns {Object} context
     */
    _getFilterContext: function (filter) {
        var context = {};
        if (filter.type === 'favorite') {
            _.extend(context, filter.context);
        }
        // the following code aims to restore this:
        // https://github.com/odoo/odoo/blob/master/addons/web/static/src/js/views/search/search_inputs.js#L498
        // this is required for the helpdesk tour to pass
        // this seems weird to only do that for m2o fields, but a test fails if
        // we do it for other fields (my guess being that the test should simply
        // be adapted)
        if (filter.type === 'field' && filter.isDefault) {
            if (this.fields[filter.attrs.name].type === 'many2one') {
                var value = filter.defaultValue;
                // the following if required to make the main_flow_tour pass (see
                // https://github.com/odoo/odoo/blob/master/addons/web/static/src/js/views/search/search_inputs.js#L461)
                if (_.isArray(filter.defaultValue)) {
                    value = filter.defaultValue[0];
                }
                context['default_' + filter.attrs.name] = value;
            }
        }
        return context;
    },
    /**
     * Compute (if possible) the domain of the provided filter.
     *
     * @private
     * @param {Object} filter
     * @returns {string|undefined} domain, string representation of a domain
     */
    _getFilterDomain: function (filter) {
        var domain;
        if (filter.type === 'filter') {
            domain = filter.domain;
            if (filter.domain === undefined) {
                domain = Domain.prototype.constructDomain(
                    filter.fieldName,
                    filter.currentOptionId,
                    filter.fieldType
                );
            }
        }
        if (filter.type === 'favorite') {
            domain = filter.domain;
        }
        if (filter.type === 'field') {
            domain = filter.domain;
        }
        return domain;
    },
    /**
     * Compute the groupBys (if possible) of the provided filter.
     *
     * @private
     * @param {Object} filter
     * @returns {string[]|undefined} groupBys
     */
    _getFilterGroupBys: function (filter) {
        var groupBys;
        if (filter.type === 'groupBy') {
            var groupBy = filter.fieldName;
            if (filter.currentOptionId) {
                groupBy = groupBy + ':' + filter.currentOptionId;
            }
            groupBys = [groupBy];
        }
        if (filter.type === 'favorite') {
            groupBys = filter.groupBys;
        }
        return groupBys;
    },
    /**
     * Return the concatenation of groupBys comming from the active filters.
     * The array this.query encoding the order in which the groups have been
     * activated, the results respect the appropriate logic: the groupBys
     * coming from an active favorite (if any) come first, then come the
     * groupBys comming from the active filters of type 'groupBy'.
     *
     * @private
     * @returns {string[]} groupBys
     */
    _getGroupBy: function () {
        var self = this;
        var groupBys = this.query.reduce(
            function (acc, groupId) {
                var group = self.groups[groupId];
                return acc.concat(self._getGroupGroupBys(group));
            },
            []
        );
        return groupBys;
    },
    /**
     * Return the list of the contexts of the filters acitve in the given
     * group.
     *
     * @private
     * @param {Object} group
     * @returns {Object[]}
     */
    _getGroupContexts: function (group) {
        var self = this;
        var contexts = group.activeFilterIds.map(function (filterId) {
            var filter = self.filters[filterId];
            return self._getFilterContext(filter);
        });
        return _.compact(contexts);
    },
    /**
     * Return the string representation of a domain created by combining
     * appropriately (with an 'OR') the domains coming from the filters
     * active in the given group.
     *
     * @private
     * @param {Object} group
     * @returns {string} string representation of a domain
     */
    _getGroupDomain: function (group) {
        var self = this;
        var domains = group.activeFilterIds.map(function (filterId) {
            var filter = self.filters[filterId];
            return self._getFilterDomain(filter);
        });
        return pyUtils.assembleDomains(_.compact(domains), 'OR');
    },
    /**
     * Return the groupBys coming form the filtes active in the given group.
     *
     * @private
     * @param {Object} group
     * @returns {string[]}
     */
    _getGroupGroupBys: function (group) {
        var self = this;
        var groupBys = group.activeFilterIds.reduce(
            function (acc, filterId) {
                var filter = self.filters[filterId];
                acc = acc.concat(self._getFilterGroupBys(filter));
                return acc;
            },
            []
        );
        return _.compact(groupBys);
    },
    /**
     * Return the id of the group with the provided type.
     *
     * @private
     * @param {'groupBy'|'favorite'|'timeRange'} type
     * @returns {string}
     */
    _getGroupIdOfType: function (type) {
        var self = this;
        return Object.keys(this.groups).find(function (groupId) {
            var group = self.groups[groupId];
            return group.type === type;
        });
    },
    /**
     * Used to get the key orderedBy of a favorite.
     *
     * @private
     * @returns {Object[]} orderedBy
     */
    _getOrderedBy: function () {
        var orderedBy;
        var id = this._getGroupIdOfType('favorite');
        if (this.query.indexOf(id) !== -1) {
            // if we are here, this means that the group of favorite is
            // active and activeFilterIds is a list of length one.
            var group = this.groups[id];
            var activeFavoriteId = group.activeFilterIds[0];
            var favorite = this.filters[activeFavoriteId];
            orderedBy = favorite.orderedBy;
        }
        return orderedBy;
    },
    /**
     * Return the list of the contexts of active filters.
     *
     * @private
     * @returns {Object[]}
     */
    _getQueryContext: function () {
        var self = this;
        var contexts = this.query.reduce(
            function (acc, groupId) {
                var group = self.groups[groupId];
                acc = acc.concat(self._getGroupContexts(group));
                return acc;
            },
            []
        );
        return _.compact(contexts);
    },
    /**
     * Return an empty object or an object with a key timeRangeMenuData
     * containing info on time ranges and their descriptions if a filter of type
     * 'timeRange' is activated (only one can be).
     * The key timeRange and comparisonTimeRange will be string or array
     * representation of domains according to the value of evaluation:
     * array if evaluation is true, string if false.
     *
     * @private
     * @param {boolean} [evaluation=false]
     * @returns {Object}
     */
    _getTimeRangeMenuData: function (evaluation) {
        var context = {};
        // groupOfTimeRanges can be undefined in case with withSearchBar is false
        var groupOfTimeRanges = this.groups[this._getGroupIdOfType('timeRange')];
        if (groupOfTimeRanges && groupOfTimeRanges.activeFilterIds.length) {
            var filter = this.filters[groupOfTimeRanges.activeFilterIds[0]];

            var comparisonTimeRange = "[]";
            var comparisonTimeRangeDescription;

            var timeRange = Domain.prototype.constructDomain(
                    filter.fieldName,
                    filter.timeRangeId,
                    filter.fieldType
                );
            var timeRangeDescription = filter.timeRangeOptions.find(function (option) {
                return option.optionId === filter.timeRangeId;
            }).description.toString();
            if (filter.comparisonTimeRangeId) {
                comparisonTimeRange = Domain.prototype.constructDomain(
                    filter.fieldName,
                    filter.timeRangeId,
                    filter.fieldType,
                    null,
                    filter.comparisonTimeRangeId
                );
                comparisonTimeRangeDescription = filter.comparisonTimeRangeOptions.find(function (comparisonOption) {
                    return comparisonOption.optionId === filter.comparisonTimeRangeId;
                }).description.toString();
            }
            if (evaluation) {
                timeRange = Domain.prototype.stringToArray(timeRange);
                comparisonTimeRange = Domain.prototype.stringToArray(comparisonTimeRange);
            }
            context = {
                timeRangeMenuData: {
                    timeRange: timeRange,
                    timeRangeDescription: timeRangeDescription,
                    comparisonTimeRange: comparisonTimeRange,
                    comparisonTimeRangeDescription: comparisonTimeRangeDescription,
                }
            };
        }
        return context;
    },
    /**
     * Load custom filters in db, then create a group of type 'favorite' and a
     * filter of type 'favorite' for each loaded custom filters.
     * The new filters are put in the new group.
     * Finally, if there exists (a necessarily unique) default favorite, it is activated
     * if this.activateDefaultFavorite is true.
     *
     * @private
     * @returns {Deferred}
     */
    _loadFavorites: function () {
        var self = this;
        var def = this.loadFilters(this.modelName,this.actionId).then(function (favorites) {
            if (favorites.length) {
                favorites = favorites.map(function (favorite) {
                    var userId = favorite.user_id ? favorite.user_id[0] : false;
                    var groupNumber = userId ? 1 : 2;
                    var context = pyUtils.eval('context', favorite.context, session.user_context);
                    var groupBys = [];
                    if (context.group_by) {
                        groupBys = context.group_by;
                        delete context.group_by;
                    }
                    var sort = JSON.parse(favorite.sort);
                    var orderedBy = sort.map(function (order) {
                        var orderTerms = order.split(' ');
                        return {
                            name: orderTerms[0],
                            asc: orderTerms.length === 2 && orderTerms[1] === 'asc',
                        };
                    });
                    return {
                        type: 'favorite',
                        description: favorite.name,
                        isRemovable: true,
                        groupNumber: groupNumber,
                        isDefault: favorite.is_default,
                        domain: favorite.domain,
                        groupBys: groupBys,
                        // we want to keep strings as long as possible
                        context: favorite.context,
                        orderedBy: orderedBy,
                        userId: userId,
                        serverSideId: favorite.id,
                    };
                });
                self._createGroupOfFilters(favorites);
                if (self.activateDefaultFavorite) {
                    var defaultFavoriteId = Object.keys(self.filters).find(function (filterId) {
                        var filter = self.filters[filterId];
                        return filter.type === 'favorite' && filter.isDefault;
                    });
                    if (defaultFavoriteId) {
                        self.toggleFilter(defaultFavoriteId);
                    }
                }
            } else {
                self._createEmptyGroup('favorite');
            }
        });
        return def;
    },
    /**
     * Load search defaults and set the `domain` key on filter (of type `field`).
     * Some search defaults need to fetch data (like m2o for example) so this
     * is asynchronous.
     *
     * @private
     * @returns {Deferred[]}
     */
    _loadSearchDefaults: function () {
        var self = this;
        var defs = [];
        _.each(this.filters, function (filter) {
            if (filter.type === 'field' && filter.isDefault) {
                var def;
                var field = self.fields[filter.attrs.name];
                var value = filter.defaultValue;
                if (field.type === 'many2one') {
                    if (value instanceof Array) {
                        // M2O search fields do not currently handle multiple default values
                        // there are many cases of {search_default_$m2ofield: [id]}, need
                        // to handle this as if it were a single value.
                        value = value[0];
                    }
                    def = self._rpc({
                        model: field.relation,
                        method: 'name_get',
                        args: [value],
                        context: self.actionContext,
                    }).then(function (result) {
                        var autocompleteValue = {
                            label: result[0][1],
                            value: value,
                        };
                        filter.autoCompleteValues.push(autocompleteValue);
                        filter.domain = self._getAutoCompletionFilterDomain(filter);
                    });
                } else {
                    var autocompleteValue;
                    if (field.type === 'selection') {
                        var match = _.find(field.selection, function (sel) {
                            return sel[0] === value;
                        });
                        autocompleteValue = {
                            label: match[1],
                            value: match[0],
                        };
                    } else {
                        autocompleteValue = {
                            label: String(value),
                            value: value,
                        };
                    }
                    filter.autoCompleteValues.push(autocompleteValue);
                    filter.domain = self._getAutoCompletionFilterDomain(filter);
                }
                if (def) {
                    defs.push(def);
                }
            }
        });
        return defs;
    },
    /**
     * Compute the search Query and save it as an ir.filter in db.
     * No evaluation of domains is done in order to keep them dynamic.
     * If the operatio is successful, a new filter of type 'favorite' is
     * created and activated.
     *
     * @private
     * @param {Object} favorite
     * @returns {Deferred}
     */
    _saveQuery: function (favorite) {
        var self = this;
        var userContext = session.user_context;
        var controllerQueryParams;
        this.trigger_up('get_controller_query_params', {
            callback: function (state) {
                controllerQueryParams = state;
            },
        });
        var queryContext = this._getQueryContext();
        var timeRangeMenuInfo = this._getTimeRangeMenuData(false);
        var context = pyUtils.eval(
            'contexts',
            [userContext, controllerQueryParams.context, timeRangeMenuInfo].concat(queryContext)
        );
        context = _.omit(context, Object.keys(userContext));
        var groupBys = this._getGroupBy();
        if (groupBys.length) {
            context.group_by = groupBys;
        }
        var domain = this._getDomain();
        var userId = favorite.isShared ? false : session.uid;
        var orderedBy = this._getOrderedBy() || [];
        if (controllerQueryParams.orderedBy) {
            orderedBy = controllerQueryParams.orderedBy;
        }
        var sort = orderedBy.map(function (order) {
                return order.name + ((order.asc === false) ? " desc" : "");
        });

        var irFilter = {
            name: favorite.description,
            context: context,
            domain: domain,
            is_default: favorite.isDefault,
            user_id: userId,
            model_id: this.modelName,
            action_id: this.actionId,
            sort: JSON.stringify(sort),
        };
        return this.createFilter(irFilter).then(function (serverSideId) {
            // we don't want the groupBys to be located in the context in control panel model
            delete context.group_by;
            favorite.isRemovable = true;
            favorite.groupNumber = userId ? 1 : 2;
            favorite.context = context;
            favorite.groupBys = groupBys;
            favorite.domain = domain;
            favorite.orderedBy = orderedBy;
            // not sure keys are usefull
            favorite.userId = userId;
            favorite.serverSideId = serverSideId;
            self._addNewFavorite(favorite);
        });
    },
});

return ControlPanelModel;

});
