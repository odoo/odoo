odoo.define("web/static/src/js/control_panel/control_panel_model_extension.js", function (require) {
    "use strict";

    const ActionModel = require("web/static/src/js/views/action_model.js");
    const Domain = require('web.Domain');
    const pyUtils = require('web.py_utils');

    const { DEFAULT_INTERVAL, DEFAULT_PERIOD,
        getComparisonOptions, getIntervalOptions, getPeriodOptions,
        constructDateDomain, rankInterval, yearSelected } = require('web.searchUtils');

    const FAVORITE_PRIVATE_GROUP = 1;
    const FAVORITE_SHARED_GROUP = 2;
    const DISABLE_FAVORITE = "search_disable_custom_filters";

    let filterId = 1;
    let groupId = 1;
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
     *      @prop {string} type 'filter'|'groupBy'|'comparison'|'field'|'favorite'
     *
     * Other properties can be present according to the corresponding filter type:
     *
     * • type 'comparison':
     *      @prop {string} comparisonOptionId option identifier (@see COMPARISON_OPTIONS).
     *      @prop {string} dateFilterId the id of a date filter (filter of type 'filter'
     *                                      with isDateFilter=true)
     *
     * • type 'filter':
     *      @prop {number} groupNumber used to separate items in the 'Filters' menu
     *      @prop {string} [context] context
     *      @prop {boolean} [invisible] determine if the filter is accessible in the interface
     *      @prop {boolean} [isDefault]
     *      @if isDefault = true:
     *          > @prop {number} [defaultRank=-5] used to determine the order of
     *          >                activation of default filters
     *      @prop {boolean} [isDateFilter] true if the filter comes from an arch node
     *                      with a valid 'date' attribute.
     *      @if isDateFilter = true
     *          > @prop {boolean} [hasOptions=true]
     *          > @prop {string} defaultOptionId option identifier determined by
     *          >                default_period attribute (@see PERIOD_OPTIONS).
     *          >                Default set to DEFAULT_PERIOD.
     *          > @prop {string} fieldName determined by the value of 'date' attribute
     *          > @prop {string} fieldType 'date' or 'datetime', type of the corresponding field
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
     *      @prop {Object} [comparison] of the form {comparisonId, fieldName, fieldDescription,
     *                      range, rangeDescription, comparisonRange, comparisonRangeDescription, }
     *      @prop {Object} context
     *      @prop {string} domain
     *      @prop {string[]} groupBys
     *      @prop {number} groupNumber 1 | 2, 2 if the favorite is shared
     *      @prop {string[]} orderedBy
     *      @prop {boolean} [removable=true] indicates that the favorite can be deleted
     *      @prop {number} serverSideId
     *      @prop {number} userId
     *      @prop {boolean} [isDefault]
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
     * • type 'comparison':
     *      @prop {string} dateFilterId the id of a date filter (filter of type 'filter'
     *                                      with hasOptions=true)
     *      @prop {string} type 'comparison', help when searching if a comparison is active
     *
     * • type 'filter' with hasOptions=true:
     *      @prop {string} optionId option identifier (@see PERIOD_OPTIONS)
     *
     * • type 'groupBy' with hasOptions=true:
     *      @prop {string} optionId option identifier (@see INTERVAL_OPTIONS)
     *
     * • type 'field':
     *      @prop {string} label description put in the facet (can be temporarilly missing)
     *      @prop {(string|number)} value used as the value of the generated domain
     *      @prop {string} operator used as the operator of the generated domain
     *
     * The query elements indicates what are the active filters and 'how' they are active.
     * The key groupId has been added for simplicity. It could have been removed from query elements
     * since the information is available on the corresponding filters.
     * @extends ActionModel.Extension
     */
    class ControlPanelModelExtension extends ActionModel.Extension {
        /**
         * @param {Object} config
         * @param {(string|number)} config.actionId
         * @param {Object} config.env
         * @param {string} config.modelName
         * @param {Object} [config.context={}]
         * @param {Object[]} [config.archNodes=[]]
         * @param {Object[]} [config.dynamicFilters=[]]
         * @param {string[]} [config.searchMenuTypes=[]]
         * @param {Object} [config.favoriteFilters={}]
         * @param {Object} [config.fields={}]
         * @param {boolean} [config.withSearchBar=true]
         */
        constructor() {
            super(...arguments);

            this.actionContext = Object.assign({}, this.config.context);
            this.searchMenuTypes = this.config.searchMenuTypes || [];
            this.favoriteFilters = this.config.favoriteFilters || [];
            this.fields = this.config.fields || {};
            this.searchDefaults = {};
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

            this.referenceMoment = moment();
            this.optionGenerators = getPeriodOptions(this.referenceMoment);
            this.intervalOptions = getIntervalOptions();
            this.comparisonOptions = getComparisonOptions();
        }

        //---------------------------------------------------------------------
        // Public
        //---------------------------------------------------------------------

        /**
         * @override
         * @returns {any}
         */
        get(property, ...args) {
            switch (property) {
                case "context": return this.getContext();
                case "domain": return this.getDomain();
                case "facets": return this._getFacets();
                case "filters": return this._getFilters(...args);
                case "groupBy": return this.getGroupBy();
                case "orderedBy": return this.getOrderedBy();
                case "timeRanges": return this.getTimeRanges();
            }
        }

        /**
         * @override
         */
        async load() {
            await Promise.all(this.labelPromises);
        }

        /**
         * @override
         */
        prepareState() {
            Object.assign(this.state, {
                filters: {},
                query: [],
            });
            if (this.config.withSearchBar !== false) {
                this._addFilters();
                this._activateDefaultFilters();
            }
        }

        //---------------------------------------------------------------------
        // Actions / Getters
        //---------------------------------------------------------------------

        /**
         * @returns {Object | undefined}
         */
        get activeComparison() {
            return this.state.query.find(queryElem => queryElem.type === 'comparison');
        }

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
            this._checkComparisonStatus();
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
         * @returns {Object}
         */
        getContext() {
            const groups = this._getGroups();
            return this._getContext(groups);
        }

        /**
         * @returns {Array[]}
         */
        getDomain() {
            const groups = this._getGroups();
            const userContext = this.env.session.user_context;
            try {
                return Domain.prototype.stringToArray(this._getDomain(groups), userContext);
            } catch (err) {
                throw new Error(
                    `${this.env._t("Control panel model extension failed to evaluate domain")}:/n${JSON.stringify(err)}`
                );
            }
        }

        /**
         * @returns {string[]}
         */
        getGroupBy() {
            const groups = this._getGroups();
            return this._getGroupBy(groups);
        }

        /**
         * @returns {string[]}
         */
        getOrderedBy() {
            const groups = this._getGroups();
            return this._getOrderedBy(groups);
        }

        /**
         * @returns {Object}
         */
        getTimeRanges() {
            const requireEvaluation = true;
            return this._getTimeRanges(requireEvaluation);
        }

        /**
         * Used to call dispatch and trigger a 'search'.
         */
        search() {
            /* ... */
        }

        /**
         * Activate/Deactivate a filter of type 'comparison' with provided id.
         * At most one filter of type 'comparison' can be activated at every time.
         * @param {string} filterId
         */
        toggleComparison(filterId) {
            const { groupId, dateFilterId } = this.state.filters[filterId];
            const queryElem = this.state.query.find(queryElem =>
                queryElem.type === 'comparison' &&
                queryElem.filterId === filterId
            );
            // make sure only one comparison can be active
            this.state.query = this.state.query.filter(queryElem => queryElem.type !== 'comparison');
            if (!queryElem) {
                this.state.query.push({ groupId, filterId, dateFilterId, type: 'comparison', });
            }
        }

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
            const option = this.optionGenerators.find(o => o.id === optionId);

            const index = this.state.query.findIndex(
                queryElem => queryElem.filterId === filterId && queryElem.optionId === optionId
            );

            if (index >= 0) {
                this.state.query.splice(index, 1);
                if (filter.type === 'filter' && !yearSelected(this._getSelectedOptionIds(filterId))) {
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
                if (filter.type === 'filter' && !yearSelected(this._getSelectedOptionIds(filterId))) {
                    // Here we add 'this_year' as options if no option of type
                    // year is already selected.
                    this.state.query.push({
                        groupId: filter.groupId,
                        filterId,
                        optionId: option.defaultYearId,
                    });
                }
            }
            if (filter.type === 'filter') {
                this._checkComparisonStatus();
            }
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * Activate the default favorite (if any) or all default filters.
         * @private
         */
        _activateDefaultFilters() {
            if (this.defaultFavoriteId) {
                // Activate default favorite
                this.toggleFilter(this.defaultFavoriteId);
            } else {
                // Activate default filters
                Object.values(this.state.filters)
                    .filter((f) => f.isDefault && f.type !== 'favorite')
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
        }

        /**
         * This function populates the 'filters' object at initialization.
         * The filters come from:
         *     - config.archNodes (types 'comparison', 'filter', 'groupBy', 'field'),
         *     - config.dynamicFilters (type 'filter'),
         *     - config.favoriteFilters (type 'favorite'),
         *     - code itself (type 'timeRange')
         * @private
         */
        _addFilters() {
            this._createGroupOfFavorites();
            this._createGroupOfFiltersFromArch();
            this._createGroupOfDynamicFilters();
        }

        /**
         * If a comparison is active, check if it should become inactive.
         * The comparison should become inactive if the corresponding date filter has become
         * inactive.
         * @private
         */
        _checkComparisonStatus() {
            const activeComparison = this.activeComparison;
            if (!activeComparison) {
                return;
            }
            const { dateFilterId } = activeComparison;
            const dateFilterIsActive = this.state.query.some(
                queryElem => queryElem.filterId === dateFilterId
            );
            if (!dateFilterIsActive) {
                this.state.query = this.state.query.filter(
                    queryElem => queryElem.type !== 'comparison'
                );
            }
        }

        /**
         * Returns the active comparison timeRanges object.
         * @private
         * @param {Object} comparisonFilter
         * @returns {Object | null}
         */
        _computeTimeRanges(comparisonFilter) {
            const { filterId } = this.activeComparison;
            if (filterId !== comparisonFilter.id) {
                return null;
            }
            const { dateFilterId, comparisonOptionId } = comparisonFilter;
            const {
                fieldName,
                fieldType,
                description: dateFilterDescription,
            } = this.state.filters[dateFilterId];

            const selectedOptionIds = this._getSelectedOptionIds(dateFilterId);

            // compute range and range description
            const { domain: range, description: rangeDescription } = constructDateDomain(
                this.referenceMoment, fieldName, fieldType, selectedOptionIds,
            );

            // compute comparisonRange and comparisonRange description
            const {
                domain: comparisonRange,
                description: comparisonRangeDescription,
            } = constructDateDomain(
                this.referenceMoment, fieldName, fieldType, selectedOptionIds, comparisonOptionId
            );

            return {
                comparisonId: comparisonOptionId,
                fieldName,
                fieldDescription: dateFilterDescription,
                range,
                rangeDescription,
                comparisonRange,
                comparisonRangeDescription,
            };
        }

        /**
         * Starting from the array of date filters, create the filters of type
         * 'comparison'.
         * @private
         * @param {Object[]} dateFilters
         */
        _createGroupOfComparisons(dateFilters) {
            const preFilters = [];
            for (const dateFilter of dateFilters) {
                for (const comparisonOption of this.comparisonOptions) {
                    const { id: dateFilterId, description } = dateFilter;
                    const preFilter = {
                        type: 'comparison',
                        comparisonOptionId: comparisonOption.id,
                        description: `${description}: ${comparisonOption.description}`,
                        dateFilterId,
                    };
                    preFilters.push(preFilter);
                }
            }
            this._createGroupOfFilters(preFilters);
        }

        /**
         * Add filters of type 'filter' determined by the key array dynamicFilters.
         * @private
         */
        _createGroupOfDynamicFilters() {
            const dynamicFilters = this.config.dynamicFilters || [];
            const pregroup = dynamicFilters.map(filter => {
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
         * Add filters of type 'favorite' determined by the array this.favoriteFilters.
         * @private
         */
        _createGroupOfFavorites() {
            const activateFavorite = DISABLE_FAVORITE in this.actionContext ?
                !this.actionContext[DISABLE_FAVORITE] :
                true;
            this.favoriteFilters.forEach(irFilter => {
                const favorite = this._irFilterToFavorite(irFilter);
                this._createGroupOfFilters([favorite]);
                if (activateFavorite && favorite.isDefault) {
                    this.defaultFavoriteId = favorite.id;
                }
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
                if (!this.defaultFavoriteId && filter.isDefault && filter.type === 'field') {
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
            const preFilters = this.config.archNodes.reduce(
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
                    if (preFilter.attrs && JSON.parse(preFilter.attrs.modifiers || '{}').invisible) {
                        filter.invisible = true;
                        let preFilterFieldName = null;
                        if (preFilter.tag === 'filter' && preFilter.attrs.date) {
                            preFilterFieldName = preFilter.attrs.date;
                        } else if (preFilter.tag === 'groupBy') {
                            preFilterFieldName = preFilter.attrs.fieldName;
                        }
                        if (preFilterFieldName && !this.fields[preFilterFieldName]) {
                            // In some case when a field is limited to specific groups
                            // on the model, we need to ensure to discard related filter
                            // as it may still be present in the view (in 'invisible' state)
                            return;
                        }
                    }
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
            const dateFilters = Object.values(this.state.filters).filter(
                (filter) => filter.isDateFilter
            );
            if (dateFilters.length) {
                this._createGroupOfComparisons(dateFilters);
            }
        }

        /**
         * Returns null or a copy of the provided filter with additional information
         * used only outside of the control panel model, like in search bar or in the
         * various menus. The value null is returned if the filter should not appear
         * for some reason.
         * @private
         * @param {Object} filter
         * @param {Object[]} filterQueryElements
         * @returns {Object | null}
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
                case 'comparison': {
                    const { dateFilterId } = filter;
                    const dateFilterIsActive = this.state.query.some(
                        queryElem => queryElem.filterId === dateFilterId
                    );
                    if (!dateFilterIsActive) {
                        return null;
                    }
                    break;
                }
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
            if (child.attrs.name in this.searchDefaults) {
                child.attrs.isDefault = true;
                let value = this.searchDefaults[child.attrs.name];
                if (child.tag === 'field') {
                    child.attrs.defaultValue = Array.isArray(value) ? value[0] : value;
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
            switch (filter.type) {
                case 'filter':
                    if (attrs.context) {
                        filter.context = attrs.context;
                    }
                    if (attrs.date) {
                        filter.isDateFilter = true;
                        filter.hasOptions = true;
                        filter.fieldName = attrs.date;
                        filter.fieldType = this.fields[attrs.date].type;
                        filter.defaultOptionId = attrs.default_period || DEFAULT_PERIOD;
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
                case 'field': {
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
                        let operator = filter.operator;
                        if (!operator) {
                            const type = attrs.widget || filter.fieldType;
                            // Note: many2one as a default filter will have a
                            // numeric value instead of a string => we want "="
                            // instead of "ilike".
                            if (["char", "html", "many2many", "one2many", "text"].includes(type)) {
                                operator = "ilike";
                            } else {
                                operator = "=";
                            }
                        }
                        filter.defaultRank = -10;
                        filter.defaultAutocompleteValue = {
                            operator,
                            value: attrs.defaultValue,
                        };
                    }
                    break;
                }
            }
            if (filter.fieldName && !attrs.string) {
                const { string } = this.fields[filter.fieldName];
                filter.description = string;
            }
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
                action_id: this.config.actionId,
                model_id: this.config.modelName,
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
            if ('comparison' in favorite) {
                context.comparison = favorite.comparison;
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
        _getContext(groups) {
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
         * Compute the string representation or the description of the current domain associated
         * with a date filter starting from its corresponding query elements.
         * @private
         * @param {Object} filter
         * @param {Object[]} filterQueryElements
         * @param {'domain'|'description'} [key='domain']
         * @returns {string}
         */
        _getDateFilterDomain(filter, filterQueryElements, key = 'domain') {
            const { fieldName, fieldType } = filter;
            const selectedOptionIds = filterQueryElements.map(queryElem => queryElem.optionId);
            const dateFilterRange = constructDateDomain(
                this.referenceMoment, fieldName, fieldType, selectedOptionIds,
            );
            return dateFilterRange[key];
        }

        /**
         * Return the string or array representation of a domain created by combining
         * appropriately (with an 'AND') the domains coming from the active groups
         * of type 'filter', 'favorite', and 'field'.
         * @private
         * @param {Object[]} groups
         * @returns {string}
         */
        _getDomain(groups) {
            const types = ['filter', 'favorite', 'field'];
            const domains = [];
            for (const group of groups) {
                if (types.includes(group.type)) {
                    domains.push(this._getGroupDomain(group));
                }
            }
            return pyUtils.assembleDomains(domains, 'AND');
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
                    // filter, favorite and comparison
                    facetDescription = filter.description;
                    if (filter.isDateFilter) {
                        const description = this._getDateFilterDomain(
                            filter, filterQueryElements, 'description'
                        );
                        facetDescription += `: ${description}`;
                    }
                    facetDescriptions.push(facetDescription);
                }
            }
            return facetDescriptions;
        }

        /**
         * @returns {Object[]}
         */
        _getFacets() {
            const facets = this._getGroups().map(({ activities, type, id }) => {
                const values = this._getFacetDescriptions(activities, type);
                const title = activities[0].filter.description;
                return { groupId: id, title, type, values };
            });
            return facets;
        }

        /**
         * Return an array containing enriched copies of the filters of the provided type.
         * @param {Function} predicate
         * @returns {Object[]}
         */
        _getFilters(predicate) {
            const filters = [];
            Object.values(this.state.filters).forEach(filter => {
                if ((!predicate || predicate(filter)) && !filter.invisible) {
                    const filterQueryElements = this.state.query.filter(
                        queryElem => queryElem.filterId === filter.id
                    );
                    const enrichedFilter = this._enrichFilterCopy(filter, filterQueryElements);
                    if (enrichedFilter) {
                        filters.push(enrichedFilter);
                    }
                }
            });
            if (filters.some(f => f.type === 'favorite')) {
                filters.sort((f1, f2) => f1.groupNumber - f2.groupNumber);
            }
            return filters;
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
                const { dateFilterId } = this.activeComparison || {};
                if (this.searchMenuTypes.includes('comparison') && dateFilterId === filter.id) {
                    return "[]";
                }
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
         * @returns {Object[]}
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
         * Starting from the id of a date filter, returns the array of option ids currently selected
         * for the corresponding filter.
         * @private
         * @param {string} dateFilterId
         * @returns {string[]}
         */
        _getSelectedOptionIds(dateFilterId) {
            const selectedOptionIds = [];
            for (const queryElem of this.state.query) {
                if (queryElem.filterId === dateFilterId) {
                    selectedOptionIds.push(queryElem.optionId);
                }
            }
            return selectedOptionIds;
        }

        /**
         * Returns the last timeRanges object found in the query.
         * TimeRanges objects can be associated with filters of type 'favorite'
         * or 'comparison'.
         * @private
         * @param {boolean} [evaluation=false]
         * @returns {Object | null}
         */
        _getTimeRanges(evaluation) {
            let timeRanges;
            for (const queryElem of this.state.query.slice().reverse()) {
                const filter = this.state.filters[queryElem.filterId];
                if (filter.type === 'comparison') {
                    timeRanges = this._computeTimeRanges(filter);
                    break;
                } else if (filter.type === 'favorite' && filter.comparison) {
                    timeRanges = filter.comparison;
                    break;
                }
            }
            if (timeRanges) {
                if (evaluation) {
                    timeRanges.range = Domain.prototype.stringToArray(timeRanges.range);
                    timeRanges.comparisonRange = Domain.prototype.stringToArray(timeRanges.comparisonRange);
                }
                return timeRanges;
            }
            return null;
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
            let comparison;
            if (context.comparison) {
                comparison = context.comparison;
                delete context.comparison;
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
            if (comparison) {
                favorite.comparison = comparison;
            }
            return favorite;
        }

        /**
         * Group the query elements in group.activities by qe -> qe.filterId
         * and changes the form of group.activities to make it more suitable for further
         * computations.
         * @private
         * @param {Object} group
         */
        _mergeActivities(group) {
            const { activities, type } = group;
            let res = [];
            switch (type) {
                case 'filter':
                case 'groupBy': {
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
                }
                case 'favorite':
                case 'field':
                case 'comparison': {
                    // all activities in the group have same filterId
                    const { filterId } = group.activities[0];
                    const filter = this.state.filters[filterId];
                    res.push({
                        filter,
                        filterQueryElements: group.activities
                    });
                    break;
                }
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
                    if (queryElem) {
                        queryElem.label = label;
                        defaultAutocompleteValue.label = label;
                    }
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
            this.config.trigger("get-controller-query-params", params => {
                controllerQueryParams = params;
            });
            controllerQueryParams = controllerQueryParams || {};
            controllerQueryParams.context = controllerQueryParams.context || {};

            const queryContext = this._getContext(groups);
            const context = pyUtils.eval(
                'contexts',
                [userContext, controllerQueryParams.context, queryContext]
            );
            for (const key in userContext) {
                delete context[key];
            }

            const requireEvaluation = false;
            const domain = this._getDomain(groups);
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
                preFilter.comparison = timeRanges;
            }
            const irFilter = this._favoriteToIrFilter(preFilter);
            const serverSideId = await this.env.dataManager.create_filter(irFilter);

            preFilter.serverSideId = serverSideId;

            return preFilter;
        }

        //---------------------------------------------------------------------
        // Static
        //---------------------------------------------------------------------

        /**
         * @override
         * @returns {{ attrs: Object, children: Object[] }}
         */
        static extractArchInfo(archs) {
            const { attrs, children } = archs.search;
            const controlPanelInfo = {
                attrs,
                children: [],
            };
            for (const child of children) {
                if (child.tag !== "searchpanel") {
                    controlPanelInfo.children.push(child);
                }
            }
            return controlPanelInfo;
        }
    }

    ActionModel.registry.add("ControlPanel", ControlPanelModelExtension, 10);

    return ControlPanelModelExtension;
});
