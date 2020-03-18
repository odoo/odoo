odoo.define('web.ControlPanelModel', function (require) {
    "use strict";

    const Domain = require('web.Domain');
    const { Model } = require('web.model');
    const { parseArch } = require('web.viewUtils');
    const pyUtils = require('web.py_utils');

    const { COMPARISON_TIME_RANGE_OPTIONS,
        DEFAULT_INTERVAL, DEFAULT_PERIOD, FACET_ICONS,
        INTERVAL_OPTIONS, OPTION_GENERATORS,
        TIME_RANGE_OPTIONS, YEAR_OPTIONS,
        rankPeriod, rankInterval } = require('web.searchUtils');

    const FAVORITE_PRIVATE_GROUP = 1;
    const FAVORITE_SHARED_GROUP = 2;

    let filterId = 0;
    let groupId = 0;
    let groupNumber = 0;

    /**
     * Control panel model
     *
     * The control panel model state is an object structured in the following way:
     *
     *  {
     *      filters: Object{},
     *      query: Object[],
     *  }
     *
     *-------------------------------------------------------------------------
     * Filters
     *-------------------------------------------------------------------------
     *
     * The keys are stringified numbers called 'filter ids'.
     * The values are objects called 'filters'.
     *
     * Each filter has the following properties:
     *      @prop {number} id unique identifier, also the filter's corresponding key
     *      @prop {number} groupId the id of some group, actually the group itself,
     *                     the (active) 'groups' are reconstructed in _getGroups.
     *      @prop {string} description the description of the filter
     *      @prop {string} type 'filter'|'groupBy'|'timeRange'|'field'|'favorite'
     *
     * Other properties can be present according to the corresponding filter type:
     *
     * • type 'filter':
     *      @prop {number} groupNumber used to separate items in the 'Filters' menu
     *      @prop {string} [context] context
     *      @prop {boolean} [invisible] determine if the filter is accessible in the interface
     *      @prop {boolean} [isDefault]
     *      @if isDefault = true:
     *          > @prop {number} [defaultRank=-5] used to determine the order of
     *          >                activation of default filters
     *      @prop {boolean} [hasOptions] true if the filter comes from an arch node
     *                      with a valid 'date' attribute.
     *      @if hasOptions = true
     *          > @prop {string} defaultOptionId option identifier determined by
     *          >                default_period attribute (@see OPTION_GENERATORS).
     *          >                Default set to DEFAULT_PERIOD.
     *          > @prop {string} fieldName determined by the value of 'date' attribute
     *          > @prop {string} fieldType 'date' or 'datetime', type of the corresponding field
     *          > @prop {Objecŧ[]} basicDomains of the form { description, domain }[]
     *      @else
     *          > @prop {string} domain
     *
     * • type 'groupBy':
     *      @prop {string} fieldName
     *      @prop {string} fieldType
     *      @prop {number} groupNumber used to separate items in the 'Group by' menu
     *      @prop {boolean} [isDefault]
     *      @if isDefault = true:
     *          > @prop {number} defaultRank used to determine the order of activation
     *          >                of default filters
     *      @prop {boolean} [invisible] determine if the filter is accessible in the interface
     *      @prop {boolean} [hasOptions] true if field type is 'date' or 'datetime'
     *      @if hasOptions=true
     *          > @prop {string} defaultOptionId option identifier (see INTERVAL_OPTIONS)
     *                           default set to DEFAULT_INTERVAL.
     *
     * • type 'timeRange':
     *      no extra key, a single filter has that type
     *
     * • type 'field':
     *      @prop {string} fieldName
     *      @prop {string} fieldType
     *      @prop {string} [context]
     *      @prop {string} [domain]
     *      @prop {string} [filterDomain]
     *      @prop {boolean} [invisible] determine if the filter is accessible in the interface
     *      @prop {boolean} [isDefault]
     *      @prop {string} [operator]
     *      @if isDefault = true:
     *          > @prop {number} [defaultRank=-10] used to determine the order of
     *          >                activation of filters
     *          > @prop {Object} defaultAutocompleteValue of the form { value, label, operator }
     *
     * • type: 'favorite':
     *      @prop {Object} context
     *      @prop {string} domain
     *      @prop {string[]} groupBys
     *      @prop {number} groupNumber 1 | 2, 2 if the favorite is shared
     *      @prop {string[]} orderedBy
     *      @prop {boolean} [removable=true] indicates that the favorite can be deleted
     *      @prop {number} serverSideId
     *      @prop {number} userId
     *      @prop {boolean} [isDefault]
     *      @prop {Object} [timeRanges] of the form { fieldName, rangeId[, comparisonRangeId] }
     *
     *-------------------------------------------------------------------------
     * Query
     *-------------------------------------------------------------------------
     *
     * The query elements are objects called 'query elements'.
     *
     * Each query element has the following properties:
     *      @prop {number} filterId the id of some filter
     *      @prop {number} groupId the id of some group (actually the group itself)
     *
     * Other properties must be defined according to the corresponding filter type.
     *
     * • type 'filter' with hasOptions=true:
     *      @prop {string} optionId option identifier (@see OPTION_GENERATORS)
     *
     * • type 'groupBy' with hasOptions=true:
     *      @prop {string} optionId option identifier (@see INTERVAL_OPTIONS)
     *
     * • type 'timeRange':
     *      @prop {string} fieldName name of a field
     *      @prop {string} rangeId option identifier (see TIME_RANGE_OPTIONS)
     *      @prop {string} [comparisonRangeId] option identifier (see COMPARISON_TIME_RANGE_OPTIONS)
     *
     * • type 'field':
     *      @prop {string} label description put in the facet (can be temporarilly missing)
     *      @prop {(string|number)} value used as the value of the generated domain
     *      @prop {string} operator used as the operator of the generated domain
     *
     * The query elements indicates what are the active filters and 'how' they are active.
     * The key groupId has been added for simplicity. It could have been removed from query elements
     * since the information is available on the corresponding filters.
     * @extends Model
     */
    class ControlPanelModel extends Model {
        /**
         * @param {Object} config
         * @param {(string|number)} config.actionId
         * @param {Object} config.env
         * @param {string} config.modelName
         * @param {Object} [config.importedState]
         * @param {Array[]} [config.actionDomain=[]]
         * @param {Object} [config.actionContext={}]
         * @param {Object[]} [config.dynamicFilters=[]]
         * @param {string[]} [config.searchMenuTypes=[]]
         * @param {Object} [config.viewInfo={}]
         * @param {boolean} [config.withSearchBar=true]
         *
         */
        constructor(config) {
            super();

            this._setProperties(config);

            if (this.withSearchBar) {
                if (config.importedState) {
                    this.importState(config.importedState);
                } else {
                    this._prepareInitialState();
                }
            }

            this.isReady = Promise.all(this.labelPromises);
        }

        //---------------------------------------------------------------------
        // Public
        //---------------------------------------------------------------------

        /**
         * Activate a filter of type 'field' with given filterId with
         * 'autocompleteValues' value, label, and operator.
         * @param {Object}
         */
        addAutoCompletionValues({ filterId, label, value, operator }) {
            const queryElem = this.state.query.find(queryElem =>
                queryElem.filterId === filterId &&
                queryElem.value === value &&
                queryElem.operator === operator
            );
            if (!queryElem) {
                const { groupId } = this.state.filters[filterId];
                this.state.query.push({ filterId, groupId, label, value, operator });
            } else {
                queryElem.label = label;
            }
        }

        /**
         * Activate the unique filter of type 'timeRange' with provided 'options' fieldName, rangeId,
         * and optional comparisonRangeId.
         * @param {string} fieldName
         * @param {string} rangeId
         * @param {string} [comparisonRangeId]
         */
        activateTimeRange(fieldName, rangeId, comparisonRangeId) {
            const filter = Object.values(this.state.filters).find(f => f.type === 'timeRange');
            const detail = { fieldName, rangeId };
            if (comparisonRangeId) {
                detail.comparisonRangeId = comparisonRangeId;
            }
            const queryElem = this.state.query.find(queryElem => queryElem.filterId === filter.id);
            if (queryElem) {
                Object.assign(queryElem, detail);
                if (!comparisonRangeId) {
                    delete queryElem.comparisonRangeId;
                }
            } else {
                this.state.query.push(Object.assign({ groupId: filter.groupId, filterId: filter.id }, detail));
            }
        }

        /**
         * Remove all the query elements from query.
         */
        clearQuery() {
            this.state.query = [];
        }

        /**
         * Create a new filter of type 'favorite' and activate it.
         * A new group containing only that filter is created.
         * The query is emptied before activating the new favorite.
         * @param {Object} preFilter
         * @returns {Promise}
         */
        async createNewFavorite(preFilter) {
            const preFavorite = await this._saveQuery(preFilter);
            this.clearQuery();
            const filter = Object.assign(preFavorite, {
                groupId,
                id: filterId,
            });
            this.state.filters[filterId] = filter;
            this.state.query.push({ groupId, filterId });
            groupId++;
            filterId++;
        }

        /**
         * Create new filters of type 'filter' and activate them.
         * A new group containing only those filters is created.
         * @param {Object[]} filters
         * @returns {number[]}
         */
        createNewFilters(prefilters) {
            if (!prefilters.length) {
                return [];
            }
            const newFilterIdS = [];
            prefilters.forEach(preFilter => {
                const filter = Object.assign(preFilter, {
                    groupId,
                    groupNumber,
                    id: filterId,
                    type: 'filter',
                });
                this.state.filters[filterId] = filter;
                this.state.query.push({ groupId, filterId });
                newFilterIdS.push(filterId);
                filterId++;
            });
            groupId++;
            groupNumber++;
            return newFilterIdS;
        }

        /**
         * Create a new filter of type 'groupBy' and activate it.
         * It is added to the unique group of groupbys.
         * @param {Object} field
         */
        createNewGroupBy(field) {
            const groupBy = Object.values(this.state.filters).find(f => f.type === 'groupBy');
            const filter = {
                description: field.string || field.name,
                fieldName: field.name,
                fieldType: field.type,
                groupId: groupBy ? groupBy.groupId : groupId++,
                groupNumber,
                id: filterId,
                type: 'groupBy',
            };
            this.state.filters[filterId] = filter;
            if (['date', 'datetime'].includes(field.type)) {
                filter.hasOptions = true;
                filter.defaultOptionId = DEFAULT_INTERVAL;
                this.toggleFilterWithOptions(filterId);
            } else {
                this.toggleFilter(filterId);
            }
            groupNumber++;
            filterId++;
        }

        /**
         * Deactivate a group with provided groupId, i.e. delete the query elements
         * with given groupId.
         * @param {number} groupId
         */
        deactivateGroup(groupId) {
            this.state.query = this.state.query.filter(
                queryElem => queryElem.groupId !== groupId
            );
        }

        /**
         * Delete a filter of type 'favorite' with given filterId server side and
         * in control panel model. Of course the filter is also removed
         * from the search query.
         * @param {number} filterId
         */
        async deleteFavorite(filterId) {
            const { serverSideId } = this.state.filters[filterId];
            await this.env.dataManager.delete_filter(serverSideId);
            const index = this.state.query.findIndex(
                queryElem => queryElem.filterId === filterId
            );
            delete this.state.filters[filterId];
            if (index >= 0) {
                this.state.query.splice(index, 1);
            }
        }

        /**
         * Return the state of the control panel model (the filters and the
         * current query). This state can then be used in an other control panel
         * model (with same key modelName). See importedState.
         * @returns {Object}
         */
        exportState() {
            return JSON.parse(JSON.stringify(this.state));
        }

        /**
         * Called by search bar to render the facets
         * @returns {Object[]}
         */
        getFacets() {
            const groups = this._getGroups();
            return groups.map(group => {
                const { activities, type, id } = group;
                const facet = {
                    groupId: id,
                    separator: type === 'groupBy' ? ">" : this.env._t("or"),
                    values: this._getFacetDescriptions(activities, type),
                };
                const icon = FACET_ICONS[type];
                if (icon) {
                    facet.icon = icon;
                } else {
                    facet.title = activities[0].filter.description;
                }
                return facet;
            });
        }

        /**
         * Return an array containing enriched copies of the filters of the provided type.
         * @param {string} type
         * @returns {Object[]}
         */
        getFiltersOfType(type) {
            const filters = Object.values(this.state.filters).reduce(
                (filters, filter) => {
                    if (filter.type === type && !filter.invisible) {
                        const activities = this.state.query.filter(
                            queryElem => queryElem.filterId === filter.id
                        );
                        const enrichedFilter = this._enrichFilterCopy(filter, activities);
                        filters.push(enrichedFilter);
                    }
                    return filters;
                },
                []
            );
            if (type === 'favorite') {
                filters.sort((f1, f2) => f1.groupNumber - f2.groupNumber);
            }
            return filters;
        }

        /**
         * Principal objects used by controllers/models to fetch data.
         * @returns {Object} An object called search query with keys domain, groupBy,
         *      context, orderedBy, and (optionally) timeRanges.
         */
        getQuery() {
            const requireEvaluation = true;
            const groups = this._getGroups();
            const query = {
                context: this._getContext(groups),
                domain: this._getDomain(groups, requireEvaluation),
                groupBy: this._getGroupBy(groups),
                orderedBy: this._getOrderedBy(groups)
            };
            if (this.searchMenuTypes.includes('timeRange')) {
                const timeRanges = this._getTimeRanges(requireEvaluation);
                query.timeRanges = timeRanges || {};
            }
            return query;
        }

        /**
         * Allow to reuse the state of a previous control panel model with same modelName.
         * This is mainly used when switching views.
         * @param {Object} state
         */
        importState(state) {
            Object.assign(this.state, state);
        }

        /**
         * This function won't do anything: its purpose is to call the dispatch
         * method to trigger a 'search' event + reload the components.
         */
        search() { }

        /**
         * Activate or deactivate the simple filter with given filterId, i.e.
         * add or remove a corresponding query element.
         * @param {string} filterId
         */
        toggleFilter(filterId) {
            const index = this.state.query.findIndex(
                queryElem => queryElem.filterId === filterId
            );
            if (index >= 0) {
                this.state.query.splice(index, 1);
            } else {
                const { groupId, type } = this.state.filters[filterId];
                if (type === 'favorite') {
                    this.state.query = [];
                }
                this.state.query.push({ groupId, filterId });
            }
        }

        /**
         * Used to toggle a query element { filterId, optionId, (groupId) }.
         * This can impact the query in various form, e.g. add/remove other query elements
         * in case the filter is of type 'filter'.
         * @param {string} filterId
         * @param {string} [optionId]
         */
        toggleFilterWithOptions(filterId, optionId) {
            const filter = this.state.filters[filterId];
            optionId = optionId || filter.defaultOptionId;

            const noYearSelected = (filterId) => !this.state.query.some(queryElem => {
                return queryElem.filterId === filterId && YEAR_OPTIONS[queryElem.optionId];
            });

            const defaultYearId = (optionId) => {
                const year = this.optionGenerators.find(o => o.id === optionId).defaultYear;
                return this.optionGenerators.find(o => o.setParam.year === year).id;
            };

            const index = this.state.query.findIndex(
                queryElem => queryElem.filterId === filterId && queryElem.optionId === optionId
            );
            if (index >= 0) {
                this.state.query.splice(index, 1);
                if (filter.type === 'filter' && noYearSelected(filterId)) {
                    // This is the case where optionId was the last option
                    // of type 'year' to be there before being removed above.
                    // Since other options of type 'month' or 'quarter' do
                    // not make sense without a year we deactivate all options.
                    this.state.query = this.state.query.filter(
                        queryElem => queryElem.filterId !== filterId
                    );
                }
            } else {
                this.state.query.push({ groupId: filter.groupId, filterId, optionId });
                if (filter.type === 'filter' && noYearSelected(filterId)) {
                    // Here we add 'this_year' as options if no option of type
                    // year is already selected.
                    this.state.query.push({
                        groupId: filter.groupId,
                        filterId,
                        optionId: defaultYearId(optionId),
                    });
                }
            }
        }

        /**
         * TODO: the way it is done could be improved, but the actual state of the
         * searchView doesn't allow to do much better.
         *
         * Update the domain of the search view by adding and/or removing filters.
         * @param {Object[]} newFilters list of filters to add, described by
         *   objects with keys domain (the domain as an Array), description (the text
         *   to display in the facet) and type with value 'filter'.
         * @param {number[]} filtersToRemove list of filter ids to remove
         *   (previously added ones)
         * @returns {number[]} list of added filter ids (to pass as filtersToRemove
         *   for a further call to this function)
         */
        updateFilters(newFilters, filtersToRemove) {
            const newFilterIdS = this.createNewFilters(newFilters);
            this.state.query = this.state.query.filter(
                queryElem => !filtersToRemove.includes(queryElem.filterId)
            );
            return newFilterIdS;
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * Activate the filter of type timeRange with the options set in the key
         * time_ranges of actionContext (if any).
         * @private
         */
        _activateDefaultTimeRanges() {
            const { field, range, comparisonRange } = this.actionContext.time_ranges;
            this.activateTimeRange(field, range, comparisonRange);
        }

        /**
         * Activate the default favorite (if any) or all default filters.
         * @private
         */
        _activateDefaultFilters() {
            const defaultFilters = [];
            const defaultFavorites = [];
            for (const fId in this.state.filters) {
                if (this.state.filters[fId].isDefault) {
                    if (this.state.filters[fId].type === 'favorite') {
                        defaultFavorites.push(this.state.filters[fId]);
                    } else {
                        defaultFilters.push(this.state.filters[fId]);
                    }
                }
            }
            if (this.activateDefaultFavorite && defaultFavorites.length) {
                // Activate default favorite
                this.toggleFilter(defaultFavorites[0].id);
            } else {
                // Activate default filters
                defaultFilters
                    .sort((f1, f2) => (f1.defaultRank || 100) - (f2.defaultRank || 100))
                    .forEach(f => {
                        if (f.hasOptions) {
                            this.toggleFilterWithOptions(f.id);
                        } else if (f.type === 'field') {
                            let { operator, label, value } = f.defaultAutocompleteValue;
                            this.addAutoCompletionValues({
                                filterId: f.id,
                                value,
                                operator,
                                label,
                            });
                        } else {
                            this.toggleFilter(f.id);
                        }
                    });
            }
            if (this.actionContext.time_ranges) {
                this._activateDefaultTimeRanges();
            }
        }

        /**
         * This function populates the 'filters' object at initialization.
         * The filters come from:
         *     - config.viewInfo.arch (types 'filter', 'groupBy', 'field'),
         *     - config.dynamicFilters (type 'filter'),
         *     - config.viewInfo.favoriteFilters (type 'favorite'),
         *     - code itself (type 'timeRange')
         * @private
         */
        _addFilters() {
            this._createGroupOfFiltersFromArch();
            this._createGroupOfDynamicFilters();
            this._createGroupOfFavorites();
            this._createGroupOfTimeRanges();
        }

        /**
         * Add filters of type 'filter' determined by the key array this.dynamicFilters.
         * @private
         */
        _createGroupOfDynamicFilters() {
            const pregroup = this.dynamicFilters.map(filter => {
                return {
                    description: filter.description,
                    domain: JSON.stringify(filter.domain),
                    isDefault: true,
                    type: 'filter',
                };
            });
            this._createGroupOfFilters(pregroup);
        }

        /**
         * Add filters of type 'favorite' determined by array this.favoriteFilters.
         * @private
         */
        _createGroupOfFavorites() {
            this.favoriteFilters.forEach(irFilter => {
                const favorite = this._irFilterToFavorite(irFilter);
                this._createGroupOfFilters([favorite]);
            });
        }

        /**
         * Using a list (a 'pregroup') of 'prefilters', create new filters in `state.filters`
         * for each prefilter. The new filters belong to a same new group.
         * @private
         * @param {Object[]} pregroup, list of 'prefilters'
         * @param {string} type
         */
        _createGroupOfFilters(pregroup) {
            pregroup.forEach(preFilter => {
                const filter = Object.assign(preFilter, { groupId, id: filterId });
                this.state.filters[filterId] = filter;
                if (filter.isDefault && filter.type === 'field') {
                    this._prepareDefaultLabel(filter);
                }
                filterId++;
            });
            groupId++;
        }

        /**
         * Parse the arch of a 'search' view and create corresponding filters and groups.
         *
         * A searchview arch may contain a 'searchpanel' node, but this isn't
         * the concern of the ControlPanel (the SearchPanel will handle it).
         * Ideally, this code should whitelist the tags to take into account
         * instead of blacklisting the others, but with the current (messy)
         * structure of a searchview arch, it's way simpler to do it that way.
         * @private
         */
        _createGroupOfFiltersFromArch() {
            const children = this.parsedArch.children.filter(
                child => child instanceof Object && child.tag !== 'searchpanel'
            );
            const preFilters = children.reduce(
                (preFilters, child) => {
                    if (child.tag === 'group') {
                        return [...preFilters, ...child.children.map(c => this._evalArchChild(c))];
                    } else {
                        return [...preFilters, this._evalArchChild(child)];
                    }
                },
                []
            );
            preFilters.push({ tag: 'separator' });

            // create groups and filters
            let currentTag;
            let currentGroup = [];
            let pregroupOfGroupBys = [];

            preFilters.forEach(preFilter => {
                if (
                    preFilter.tag !== currentTag ||
                    ['separator', 'field'].includes(preFilter.tag)
                ) {
                    if (currentGroup.length) {
                        if (currentTag === 'groupBy') {
                            pregroupOfGroupBys = [...pregroupOfGroupBys, ...currentGroup];
                        } else {
                            this._createGroupOfFilters(currentGroup);
                        }
                    }
                    currentTag = preFilter.tag;
                    currentGroup = [];
                    groupNumber++;
                }
                if (preFilter.tag !== 'separator') {
                    const filter = {
                        type: preFilter.tag,
                        // we need to codify here what we want to keep from attrs
                        // and how, for now I put everything.
                        // In some sence, some filter are active (totally determined, given)
                        // and others are passive (require input(s) to become determined)
                        // What is the right place to process the attrs?
                    };
                    if (filter.type === 'filter' || filter.type === 'groupBy') {
                        filter.groupNumber = groupNumber;
                    }
                    this._extractAttributes(filter, preFilter.attrs);
                    currentGroup.push(filter);
                }
            });

            if (pregroupOfGroupBys.length) {
                this._createGroupOfFilters(pregroupOfGroupBys);
            }
        }

        /**
         * Add a single filter of type 'timeRange' to filters.
         * @private
         */
        _createGroupOfTimeRanges() {
            const pregroup = [{ type: 'timeRange' }];
            this._createGroupOfFilters(pregroup);
        }

        /**
         * The parent of the control panel (an action or a controller) is not
         * necessarily a component. So we need to notify it through a
         * mechanism different from __notifyComponents. Here we use the fact
         * that the controlPanelModel is an (owl) EventBus to communicate with
         * the parent.
         */
        _dispatch() {
            this.trigger('search', this.getQuery());
        }

        /**
         * Returns a copy of the provided filter with additional information
         * used only outside of the control panel model, like in search bar or in the
         * various menus.
         * @private
         * @param {Object} filter
         * @param {Object[]} filterQueryElements
         * @returns {Object}
         */
        _enrichFilterCopy(filter, filterQueryElements) {
            const isActive = Boolean(filterQueryElements.length);
            const f = Object.assign({ isActive }, filter);

            function _enrichOptions(options) {
                return options.map(o => {
                    const { description, id, groupNumber } = o;
                    const isActive = filterQueryElements.some(a => a.optionId === id);
                    return { description, id, groupNumber, isActive };
                });
            }

            switch (f.type) {
                case 'filter':
                    if (f.hasOptions) {
                        f.options = _enrichOptions(this.optionGenerators);
                    }
                    break;
                case 'groupBy':
                    if (f.hasOptions) {
                        f.options = _enrichOptions(this.intervalOptions);
                    }
                    break;
                case 'field':
                    f.autoCompleteValues = filterQueryElements.map(
                        ({ label, value, operator }) => ({ label, value, operator })
                    );
                    break;
                case 'timeRange':
                    if (filterQueryElements.length) {
                        const timeRange = this._extractTimeRange(filterQueryElements[0]);
                        Object.assign(f, timeRange);
                    }
                    break;
            }
            return f;
        }

        /**
         * Process a given arch node and enrich it.
         * @private
         * @param {Object} child
         * @returns {Object}
         */
        _evalArchChild(child) {
            if (child.attrs.context) {
                try {
                    const context = pyUtils.eval('context', child.attrs.context);
                    child.attrs.context = context;
                    if (context.group_by) {
                        // let us extract basic data since we just evaluated context
                        // and use a correct tag!
                        child.attrs.fieldName = context.group_by.split(':')[0];
                        child.attrs.defaultInterval = context.group_by.split(':')[1];
                        child.tag = 'groupBy';
                    }
                } catch (e) { }
            }
            if (this.searchDefaults.hasOwnProperty(child.attrs.name)) {
                child.attrs.isDefault = true;
                let value = this.searchDefaults[child.attrs.name];
                if (child.tag === 'field') {
                    if (value instanceof Array) {
                        value = value[0];
                    }
                    child.attrs.defaultAutocompleteValue = { value, operator: '=' };
                } else if (child.tag === 'groupBy') {
                    child.attrs.defaultRank = typeof value === 'number' ? value : 100;
                }
            }
            return child;
        }

        /**
         * Process the attributes set on an arch node and adds various keys to
         * the given filter.
         * @private
         * @param {Object} filter
         * @param {Object} attrs
         */
        _extractAttributes(filter, attrs) {
            if (attrs.isDefault) {
                filter.isDefault = attrs.isDefault;
            }
            filter.description = attrs.string || attrs.help || attrs.name || attrs.domain || 'Ω';
            if (attrs.invisible) {
                filter.invisible = true;
            }
            switch (filter.type) {
                case 'filter':
                    if (attrs.context) {
                        filter.context = attrs.context;
                    }
                    if (attrs.date) {
                        filter.hasOptions = true;
                        filter.fieldName = attrs.date;
                        filter.fieldType = this.fields[attrs.date].type;
                        filter.defaultOptionId = attrs.default_period || DEFAULT_PERIOD;
                        filter.basicDomains = this._getDateFilterBasicDomains(filter);
                    } else {
                        filter.domain = attrs.domain || '[]';
                    }
                    if (filter.isDefault) {
                        filter.defaultRank = -5;
                    }
                    break;
                case 'groupBy':
                    filter.fieldName = attrs.fieldName;
                    filter.fieldType = this.fields[attrs.fieldName].type;
                    if (['date', 'datetime'].includes(filter.fieldType)) {
                        filter.hasOptions = true;
                        filter.defaultOptionId = attrs.defaultInterval || DEFAULT_INTERVAL;
                    }
                    if (filter.isDefault) {
                        filter.defaultRank = attrs.defaultRank;
                    }
                    break;
                case 'field':
                    const field = this.fields[attrs.name];
                    filter.fieldName = attrs.name;
                    filter.fieldType = field.type;
                    if (attrs.domain) {
                        filter.domain = attrs.domain;
                    }
                    if (attrs.filter_domain) {
                        filter.filterDomain = attrs.filter_domain;
                    } else if (attrs.operator) {
                        filter.operator = attrs.operator;
                    }
                    if (attrs.context) {
                        filter.context = attrs.context;
                    }
                    if (filter.isDefault) {
                        filter.defaultRank = -10;
                        filter.defaultAutocompleteValue = attrs.defaultAutocompleteValue;
                    }
                    break;
            }
            if (filter.fieldName && !attrs.string) {
                const { string } = this.fields[filter.fieldName];
                filter.description = string;
            }
        }

        /**
         * For filter of type 'filter' with hasOptions=true,
         * returns an array of domains or descriptions according to key.
         * @param {Object} filter
         * @param {Object[]} filterQueryElements
         * @param {'domain'|'description'} key
         * @returns {string[]}
         */
        _extractInfoFromBasicDomains(filter, filterQueryElements, key) {
            const results = [];
            const yearIds = [];
            const otherOptionIds = [];
            filterQueryElements.forEach(({ optionId }) => {
                if (YEAR_OPTIONS[optionId]) {
                    yearIds.push(optionId);
                } else {
                    otherOptionIds.push(optionId);
                }
            });

            const sortOptionIds = (a, b) => rankPeriod(a) - rankPeriod(b);
            yearIds.sort(sortOptionIds);
            otherOptionIds.sort(sortOptionIds);

            // the following case corresponds to years selected only
            if (otherOptionIds.length === 0) {
                yearIds.forEach(yearId => {
                    const d = filter.basicDomains[yearId];
                    results.push(d[key]);
                });
            } else {
                otherOptionIds.forEach(optionId => {
                    yearIds.forEach(yearId => {
                        const d = filter.basicDomains[`${yearId}__${optionId}`];
                        results.push(d[key]);
                    });
                });
            }
            return results;
        }

        /**
         * Construct a timeRange object from the given fieldName, rangeId, comparisonRangeId
         * parameters.
         * @private
         * @param {string} fieldName
         * @param {string} rangeId
         * @param {string} comparisonRangeId
         * @returns {Object}
         */
        _extractTimeRange({ fieldName, rangeId, comparisonRangeId }) {
            const field = this.fields[fieldName];
            const timeRange = {
                fieldName,
                fieldDescription: field.string || fieldName,
                rangeId,
                range: Domain.prototype.constructDomain(fieldName, rangeId, field.type),
                rangeDescription: TIME_RANGE_OPTIONS[rangeId].description.toString(),
            };
            if (comparisonRangeId) {
                timeRange.comparisonRangeId = comparisonRangeId;
                timeRange.comparisonRange = Domain.prototype.constructDomain(
                    fieldName, rangeId, field.type, comparisonRangeId
                );
                const { description } = COMPARISON_TIME_RANGE_OPTIONS[comparisonRangeId];
                timeRange.comparisonRangeDescription = description.toString();
            }
            return timeRange;
        }

        /**
         * Returns an object irFilter serving to create an ir_filte in db
         * starting from a filter of type 'favorite'.
         * @private
         * @param {Object} favorite
         * @returns {Object}
         */
        _favoriteToIrFilter(favorite) {
            const irFilter = {
                action_id: this.actionId,
                model_id: this.modelName,
            };

            // ir.filter fields
            if ('description' in favorite) {
                irFilter.name = favorite.description;
            }
            if ('domain' in favorite) {
                irFilter.domain = favorite.domain;
            }
            if ('isDefault' in favorite) {
                irFilter.is_default = favorite.isDefault;
            }
            if ('orderedBy' in favorite) {
                const sort = favorite.orderedBy.map(
                    ob => ob.name + (ob.asc === false ? " desc" : "")
                );
                irFilter.sort = JSON.stringify(sort);
            }
            if ('serverSideId' in favorite) {
                irFilter.id = favorite.serverSideId;
            }
            if ('userId' in favorite) {
                irFilter.user_id = favorite.userId;
            }

            // Context
            const context = Object.assign({}, favorite.context);
            if ('groupBys' in favorite) {
                context.group_by = favorite.groupBys;
            }
            if ('timeRanges' in favorite) {
                const { fieldName, rangeId, comparisonRangeId } = favorite.timeRanges;
                context.time_ranges = {
                    field: fieldName,
                    range: rangeId,
                    comparisonRange: comparisonRangeId,
                };
            }
            if (Object.keys(context).length) {
                irFilter.context = context;
            }

            return irFilter;
        }

        /**
         * Return the domain resulting from the combination of the auto-completion
         * values of a filter of type 'field'.
         * @private
         * @param {Object} filter
         * @param {Object[]} filterQueryElements
         * @returns {string}
         */
        _getAutoCompletionFilterDomain(filter, filterQueryElements) {
            const domains = filterQueryElements.map(({ label, value, operator }) => {
                let domain;
                if (filter.filterDomain) {
                    domain = Domain.prototype.stringToArray(
                        filter.filterDomain,
                        {
                            self: label,
                            raw_value: value,
                        }
                    );
                } else {
                    // Create new domain
                    domain = [[filter.fieldName, operator, value]];
                }
                return Domain.prototype.arrayToString(domain);
            });
            return pyUtils.assembleDomains(domains, 'OR');
        }

        /**
         * Construct a single context from the contexts of
         * filters of type 'filter', 'favorite', and 'field'.
         * @private
         * @returns {Object}
         */
        _getContext(groups, withActionContext = true) {
            const types = ['filter', 'favorite', 'field'];
            const contexts = groups.reduce(
                (contexts, group) => {
                    if (types.includes(group.type)) {
                        contexts.push(...this._getGroupContexts(group));
                    }
                    return contexts;
                },
                []
            );
            if (withActionContext) {
                contexts.unshift(this.actionContext);
            }
            const evaluationContext = this.env.session.user_context;
            try {
                return pyUtils.eval('contexts', contexts, evaluationContext);
            } catch (err) {
                throw new Error(
                    this.env._t("Failed to evaluate search context") + ":\n" +
                    JSON.stringify(err)
                );
            }
        }

        /**
         * Construct an object containing domains based on this.referenceMoment and
         * the field associated with the provided date filter.
         * @private
         * @param {Object} filter
         * @returns {Object}
         */
        _getDateFilterBasicDomains({ fieldName, fieldType }) {
            const _constructBasicDomain = (y, o) => {
                const setParam = Object.assign({}, y.setParam, o ? o.setParam : {});
                const granularity = o ? o.granularity : y.granularity;
                const date = this.referenceMoment.clone().set(setParam);
                let leftBound = date.clone().startOf(granularity).locale('en');
                let rightBound = date.clone().endOf(granularity).locale('en');
                if (fieldType === 'date') {
                    leftBound = leftBound.format('YYYY-MM-DD');
                    rightBound = rightBound.format('YYYY-MM-DD');
                } else {
                    leftBound = leftBound.utc().format('YYYY-MM-DD HH:mm:ss');
                    rightBound = rightBound.utc().format('YYYY-MM-DD HH:mm:ss');
                }
                const domain = Domain.prototype.arrayToString([
                    '&',
                    [fieldName, '>=', leftBound],
                    [fieldName, '<=', rightBound]
                ]);
                const description = o ? o.description + " " + y.description : y.description;
                return { domain, description };
            };

            const domains = {};
            this.optionGenerators.filter(y => y.groupNumber === 2).forEach(y => {
                domains[y.id] = _constructBasicDomain(y);
                this.optionGenerators.filter(y => y.groupNumber === 1).forEach(o => {
                    domains[y.id + '__' + o.id] = _constructBasicDomain(y, o);
                });
            });
            return domains;
        }

        /**
         * Compute the string representation of the current domain associated to a date filter
         * starting from its corresponding query elements.
         * @private
         * @param {Object} filter
         * @param {Objec[]} filterQueryElements
         * @returns {string}
         */
        _getDateFilterDomain(filter, filterQueryElements) {
            const domains = this._extractInfoFromBasicDomains(filter, filterQueryElements, 'domain');
            return pyUtils.assembleDomains(domains, 'OR');
        }

        /**
         * Return the string or array representation of a domain created by combining
         * appropriately (with an 'AND') the domains coming from the active groups
         * of type 'filter', 'favorite', and 'field'.
         * @private
         * @param {Object[]} groups
         * @param {boolean} [evaluation=true]
         * @returns {string}
         */
        _getDomain(groups, evaluation = true) {
            const types = ['filter', 'favorite', 'field'];
            const domains = groups.reduce(
                (domains, group) => {
                    if (types.includes(group.type)) {
                        domains.push(this._getGroupDomain(group));
                    }
                    return domains;
                },
                []
            );
            let filterDomain = pyUtils.assembleDomains(domains, 'AND');

            if (evaluation) {
                const userContext = this.env.session.user_context;
                try {
                    return pyUtils.eval('domains', [this.actionDomain, filterDomain], userContext);
                } catch (err) {
                    throw new Error(
                        this.env._t("Failed to evaluate search domain") + ":\n" +
                        JSON.stringify(err)
                    );
                }
            } else {
                return filterDomain;
            }
        }

        /**
        * Return the context of the provided (active) filter.
        * @private
        * @param {Object} filter
        * @param {Object[]} filterQueryElements
        * @returns {Object}
        */
        _getFilterContext(filter, filterQueryElements) {
            let context = filter.context || {};
            // for <field> nodes, a dynamic context (like context="{'field1': self}")
            // should set {'field1': [value1, value2]} in the context
            if (filter.type === 'field' && filter.context) {
                context = pyUtils.eval('context',
                    filter.context,
                    { self: filterQueryElements.map(({ value }) => value) },
                );
            }
            // the following code aims to remodel this:
            // https://github.com/odoo/odoo/blob/12.0/addons/web/static/src/js/views/search/search_inputs.js#L498
            // this is required for the helpdesk tour to pass
            // this seems weird to only do that for m2o fields, but a test fails if
            // we do it for other fields (my guess being that the test should simply
            // be adapted)
            if (filter.type === 'field' && filter.isDefault && filter.fieldType === 'many2one') {
                context[`default_${filter.fieldName}`] = filter.defaultAutocompleteValue.value;
            }
            return context;
        }

        /**
         * Return the domain of the provided filter.
         * @private
         * @param {Object} filter
         * @param {Object[]} filterQueryElements
         * @returns {string} domain, string representation of a domain
         */
        _getFilterDomain(filter, filterQueryElements) {
            if (filter.type === 'filter' && filter.hasOptions) {
                return this._getDateFilterDomain(filter, filterQueryElements);
            } else if (filter.type === 'field') {
                return this._getAutoCompletionFilterDomain(filter, filterQueryElements);
            }
            return filter.domain;
        }

        /**
         * Return the groupBys of the provided filter.
         * @private
         * @param {Object} filter
         * @param {Object[]} filterQueryElements
         * @returns {string[]} groupBys
         */
        _getFilterGroupBys(filter, filterQueryElements) {
            if (filter.type === 'groupBy') {
                const fieldName = filter.fieldName;
                if (filter.hasOptions) {
                    return filterQueryElements.map(
                        ({ optionId }) => `${fieldName}:${optionId}`
                    );
                } else {
                    return [fieldName];
                }
            } else {
                return filter.groupBys;
            }
        }

        /**
         * Return the concatenation of groupBys comming from the active filters of
         * type 'favorite' and 'groupBy'.
         * The result respects the appropriate logic: the groupBys
         * coming from an active favorite (if any) come first, then come the
         * groupBys comming from the active filters of type 'groupBy' in the order
         * defined in this.state.query. If no groupBys are found, one tries to
         * find some grouBys in the action context.
         * @private
         * @param {Object[]} groups
         * @returns {string[]}
         */
        _getGroupBy(groups) {
            const groupBys = groups.reduce(
                (groupBys, group) => {
                    if (['groupBy', 'favorite'].includes(group.type)) {
                        groupBys.push(...this._getGroupGroupBys(group));
                    }
                    return groupBys;
                },
                []
            );
            const groupBy = groupBys.length ? groupBys : (this.actionContext.group_by || []);
            return typeof groupBy === 'string' ? [groupBy] : groupBy;
        }

        /**
         * Return the list of the contexts of the filters active in the given
         * group.
         * @private
         * @param {Object} group
         * @returns {Object[]}
         */
        _getGroupContexts(group) {
            const contexts = group.activities.reduce(
                (ctx, qe) => [...ctx, this._getFilterContext(qe.filter, qe.filterQueryElements)],
                []
            );
            return contexts;
        }

        /**
         * Return the string representation of a domain created by combining
         * appropriately (with an 'OR') the domains coming from the filters
         * active in the given group.
         * @private
         * @param {Object} group
         * @returns {string} string representation of a domain
         */
        _getGroupDomain(group) {
            const domains = group.activities.map(({ filter, filterQueryElements }) => {
                return this._getFilterDomain(filter, filterQueryElements);
            });
            return pyUtils.assembleDomains(domains, 'OR');
        }

        /**
         * Return the groupBys coming form the filters active in the given group.
         * @private
         * @param {Object} group
         * @returns {string[]}
         */
        _getGroupGroupBys(group) {
            const groupBys = group.activities.reduce(
                (gb, qe) => [...gb, ...this._getFilterGroupBys(qe.filter, qe.filterQueryElements)],
                []
            );
            return groupBys;
        }

        /**
         * Reconstruct the (active) groups from the query elements.
         * @private
         * @returns {Objec[]}
         */
        _getGroups() {
            const groups = this.state.query.reduce(
                (groups, queryElem) => {
                    const { groupId, filterId } = queryElem;
                    let group = groups.find(group => group.id === groupId);
                    const filter = this.state.filters[filterId];
                    if (!group) {
                        const { type } = filter;
                        group = {
                            id: groupId,
                            type,
                            activities: []
                        };
                        groups.push(group);
                    }
                    group.activities.push(queryElem);
                    return groups;
                },
                []
            );
            groups.forEach(g => this._mergeActivities(g));
            return groups;
        }

        /**
         * Used to get the key orderedBy of the active favorite.
         * @private
         * @param {Object[]} groups
         * @returns {string[]} orderedBy
         */
        _getOrderedBy(groups) {
            return groups.reduce(
                (orderedBy, group) => {
                    if (group.type === 'favorite') {
                        const favoriteOrderedBy = group.activities[0].filter.orderedBy;
                        if (favoriteOrderedBy) {
                            // Group order is reversed but inner order is kept
                            orderedBy = [...favoriteOrderedBy, ...orderedBy];
                        }
                    }
                    return orderedBy;
                },
                []
            );
        }

        /**
         * Returns the last timeRanges object found in the query.
         * TimeRanges objects can be associated with filters of type 'favorite'
         * or 'timeRange'.
         * @private
         * @param {boolean} [evaluation=false]
         * @returns {(Object|undefined)}
         */
        _getTimeRanges(evaluation = false) {
            let timeRanges;
            for (const queryElem of this.state.query.slice().reverse()) {
                const filter = this.state.filters[queryElem.filterId];
                if (filter.type === 'timeRange') {
                    timeRanges = this._extractTimeRange(queryElem);
                    break;
                } else if (filter.type === 'favorite' && filter.timeRanges) {
                    // we want to make sure that last is not observed! (it is change below in case of evaluation)
                    timeRanges = this._extractTimeRange(filter.timeRanges);
                    break;
                }
            }
            if (timeRanges) {
                if (evaluation) {
                    timeRanges.range = Domain.prototype.stringToArray(timeRanges.range);
                    if (timeRanges.comparisonRangeId) {
                        timeRanges.comparisonRange = Domain.prototype.stringToArray(
                            timeRanges.comparisonRange
                        );
                    }
                }
                return timeRanges;
            }
        }

        /**
         * Returns a filter of type 'favorite' starting from an ir_filter comming from db.
         * @private
         * @param {Object} irFilter
         * @returns {Object}
         */
        _irFilterToFavorite(irFilter) {
            let userId = irFilter.user_id || false;
            if (Array.isArray(userId)) {
                userId = userId[0];
            }
            const groupNumber = userId ? FAVORITE_PRIVATE_GROUP : FAVORITE_SHARED_GROUP;
            const context = pyUtils.eval('context', irFilter.context, this.env.session.user_context);
            let groupBys = [];
            if (context.group_by) {
                groupBys = context.group_by;
                delete context.group_by;
            }
            let timeRanges;
            if (context.time_ranges) {
                const { field, range, comparisonRange } = context.time_ranges;
                timeRanges = this._extractTimeRange({
                    fieldName: field,
                    rangeId: range,
                    comparisonRangeId: comparisonRange,
                });
                delete context.time_ranges;
            }
            let sort;
            try {
                sort = JSON.parse(irFilter.sort);
            } catch (err) {
                if (err instanceof SyntaxError) {
                    sort = [];
                } else {
                    throw err;
                }
            }
            const orderedBy = sort.map(order => {
                let fieldName;
                let asc;
                const sqlNotation = order.split(' ');
                if (sqlNotation.length > 1) {
                    // regex: \fieldName (asc|desc)?\
                    fieldName = sqlNotation[0];
                    asc = sqlNotation[1] === 'asc';
                } else {
                    // legacy notation -- regex: \-?fieldName\
                    fieldName = order[0] === '-' ? order.slice(1) : order;
                    asc = order[0] === '-' ? false : true;
                }
                return {
                    asc: asc,
                    name: fieldName,
                };
            });
            const favorite = {
                context,
                description: irFilter.name,
                domain: irFilter.domain,
                groupBys,
                groupNumber,
                orderedBy,
                removable: true,
                serverSideId: irFilter.id,
                type: 'favorite',
                userId,
            };
            if (irFilter.is_default) {
                favorite.isDefault = irFilter.is_default;
            }
            if (timeRanges) {
                favorite.timeRanges = timeRanges;
            }
            return favorite;
        }

        /**
         * Group the query elements in group.activities by qe -> qe.filterId
         * and changes the form of group.activities to make it more suitable for further
         * computations.
         * @param {Object} group
         */
        _mergeActivities(group) {
            const { activities, type } = group;
            let res = [];
            switch (type) {
                case 'filter':
                case 'groupBy':
                    for (const activity of activities) {
                        const { filterId } = activity;
                        let a = res.find(({ filter }) => filter.id === filterId);
                        if (!a) {
                            a = {
                                filter: this.state.filters[filterId],
                                filterQueryElements: []
                            };
                            res.push(a);
                        }
                        a.filterQueryElements.push(activity);
                    }
                    break;
                case 'favorite':
                case 'field':
                case 'timeRange':
                    // all activities in the group have same filterId
                    const { filterId } = group.activities[0];
                    const filter = this.state.filters[filterId];
                    res.push({
                        filter,
                        filterQueryElements: group.activities
                    });
                    break;
            }
            if (type === 'groupBy') {
                res.forEach(activity => {
                    activity.filterQueryElements.sort(
                        (qe1, qe2) => rankInterval(qe1.optionId) - rankInterval(qe2.optionId)
                    );
                });
            }
            group.activities = res;
        }

        /**
         * Set the key label in defaultAutocompleteValue used by default filters of
         * type 'field'.
         * @private
         * @param {Object} filter
         */
        _prepareDefaultLabel(filter) {
            const { id, fieldType, fieldName, defaultAutocompleteValue } = filter;
            const { selection, context, relation } = this.fields[fieldName];
            if (fieldType === 'selection') {
                defaultAutocompleteValue.label = selection.find(
                    sel => sel[0] === defaultAutocompleteValue.value
                )[1];
            } else if (fieldType === 'many2one') {
                const updateLabel = label => {
                    const queryElem = this.state.query.find(({ filterId }) => filterId === id);
                    queryElem.label = label;
                    defaultAutocompleteValue.label = label;
                };
                const promise = this.env.services.rpc({
                    args: [defaultAutocompleteValue.value],
                    context: context,
                    method: 'name_get',
                    model: relation,
                })
                    .then(results => updateLabel(results[0][1]))
                    .guardedCatch(() => updateLabel(defaultAutocompleteValue.value));
                this.labelPromises.push(promise);
            } else {
                defaultAutocompleteValue.label = defaultAutocompleteValue.value;
            }
        }

        /**
         * @private
         */
        _prepareInitialState() {
            this._addFilters();
            this._activateDefaultFilters();
        }

        /**
         * Compute the search Query and save it as an ir_filter in db.
         * No evaluation of domains is done in order to keep them dynamic.
         * If the operation is successful, a new filter of type 'favorite' is
         * created and activated.
         * @private
         * @param {Object} preFilter
         * @returns {Promise<Object>}
         */
        async _saveQuery(preFilter) {
            const groups = this._getGroups();

            const userContext = this.env.session.user_context;
            let controllerQueryParams;
            this.trigger(
                'get-controller-query-params',
                p => {
                    controllerQueryParams = p;
                }
            );
            controllerQueryParams = controllerQueryParams || {};
            controllerQueryParams.context = controllerQueryParams.context || {};

            const withoutActiveContext = false;
            const queryContext = this._getContext(groups, withoutActiveContext);
            const context = pyUtils.eval(
                'contexts',
                [userContext, controllerQueryParams.context, queryContext]
            );
            for (const key in userContext) {
                delete context[key];
            }

            const requireEvaluation = false;
            const domain = this._getDomain(groups, requireEvaluation);
            const groupBys = this._getGroupBy(groups);
            const timeRanges = this._getTimeRanges(requireEvaluation);
            const orderedBy = controllerQueryParams.orderedBy ?
                controllerQueryParams.orderedBy :
                (this._getOrderedBy(groups) || []);

            const userId = preFilter.isShared ? false : this.env.session.uid;
            delete preFilter.isShared;

            Object.assign(preFilter, {
                context,
                domain,
                groupBys,
                groupNumber: userId ? FAVORITE_PRIVATE_GROUP : FAVORITE_SHARED_GROUP,
                orderedBy,
                removable: true,
                userId,
            });
            if (timeRanges) {
                preFilter.timeRanges = timeRanges;
            }
            const irFilter = this._favoriteToIrFilter(preFilter);
            const serverSideId = await this.env.dataManager.create_filter(irFilter);

            preFilter.serverSideId = serverSideId;

            return preFilter;
        }

        /**
         * Get the filter description to use in the search bar as a facet.
         * @private
         * @param {Object} activity
         * @param {Object} activity.filter
         * @param {Object[]} activity.filterQueryElements
         * @returns {string}
         */
        _getFacetDescriptions(activities, type) {
            const facetDescriptions = [];
            if (type === 'field') {
                for (const queryElem of activities[0].filterQueryElements) {
                    facetDescriptions.push(queryElem.label);
                }
            } else if (type === 'groupBy') {
                for (const { filter, filterQueryElements } of activities) {
                    if (filter.hasOptions) {
                        for (const queryElem of filterQueryElements) {
                            const option = this.intervalOptions.find(
                                o => o.id === queryElem.optionId
                            );
                            facetDescriptions.push(filter.description + ': ' + option.description);
                        }
                    } else {
                        facetDescriptions.push(filter.description);
                    }
                }
            } else {
                let facetDescription;
                for (const { filter, filterQueryElements } of activities) {
                    if (type === 'timeRange') {
                        const tr = this._extractTimeRange(filterQueryElements[0]);
                        facetDescription = `${tr.fieldDescription}: ${tr.rangeDescription}`;
                        if (tr.comparisonRangeDescription) {
                            facetDescription += ` / ${tr.comparisonRangeDescription}`;
                        }
                    } else { // filter and favorite
                        facetDescription = filter.description;
                        if (filter.hasOptions) {
                            const descriptions = this._extractInfoFromBasicDomains(
                                filter, filterQueryElements, 'description'
                            );
                            facetDescription += `: ${descriptions.join(" / ")}`;
                        }
                    }
                    facetDescriptions.push(facetDescription);
                }
            }
            return facetDescriptions;
        }

        /**
         * Using the constructor parameter object config, set most of the properties
         * of the control panel model.
         * @private
         * @param {Object} config
         */
        _setProperties(config) {
            this.state = {
                filters: {},
                query: [],
            };
            this.env = config.env;
            this.modelName = config.modelName;
            this.actionDomain = config.actionDomain || [];
            this.actionContext = config.actionContext || {};
            this.actionId = config.actionId;
            this.withSearchBar = 'withSearchBar' in config ? config.withSearchBar : true;
            this.searchMenuTypes = config.searchMenuTypes || [];

            this.searchDefaults = [];
            for (const key in this.actionContext) {
                const match = /^search_default_(.*)$/.exec(key);
                if (match) {
                    const val = this.actionContext[key];
                    if (val) {
                        this.searchDefaults[match[1]] = val;
                    }
                    delete this.actionContext[key];
                }
            }
            this.labelPromises = [];

            const viewInfo = config.viewInfo || {};

            this.parsedArch = parseArch(viewInfo.arch || '<search/>');
            this.fields = viewInfo.fields || {};
            this.favoriteFilters = viewInfo.favoriteFilters || [];
            this.activateDefaultFavorite = 'search_disable_custom_filters' in this.actionContext ?
                !this.actionContext.search_disable_custom_filters :
                true;

            this.dynamicFilters = config.dynamicFilters || [];

            this.referenceMoment = moment();
            const setDescriptions = options => {
                return Object.values(options).map(o => {
                    const oClone = JSON.parse(JSON.stringify(o));
                    const description = o.description ?
                        o.description.toString() :
                        this.referenceMoment.clone().add(o.addParam).format(o.format);
                    return Object.assign(oClone, { description });
                });
            };
            const process = (options) => {
                return options.map(o => {
                    const date = this.referenceMoment.clone().set(o.setParam).add(o.addParam);
                    delete o.addParam;
                    o.setParam[o.granularity] = date[o.granularity]();
                    o.defaultYear = date.year();
                    return o;
                });
            };
            this.optionGenerators = process(setDescriptions(OPTION_GENERATORS));
            this.intervalOptions = setDescriptions(INTERVAL_OPTIONS);
        }
    }

    return ControlPanelModel;
});
