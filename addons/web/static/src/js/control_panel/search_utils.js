odoo.define('web.searchUtils', function (require) {
    "use strict";

    const Domain = require('web.Domain');
    const { _lt, _t } = require('web.core');
    const pyUtils = require('web.py_utils');

    // Filter menu parameters
    const FIELD_OPERATORS = {
        boolean: [
            { symbol: "=", description: _lt("is true"), value: true },
            { symbol: "!=", description: _lt("is false"), value: true },
        ],
        char: [
            { symbol: "ilike", description:_lt("contains") },
            { symbol: "not ilike", description: _lt("doesn't contain") },
            { symbol: "=", description: _lt("is equal to") },
            { symbol: "!=", description: _lt("is not equal to") },
            { symbol: "!=", description: _lt("is set"), value: false },
            { symbol: "=", description: _lt("is not set"), value: false },
        ],
        date: [
            { symbol: "=", description: _lt("is equal to") },
            { symbol: "!=", description: _lt("is not equal to") },
            { symbol: ">", description: _lt("is after") },
            { symbol: "<", description: _lt("is before") },
            { symbol: ">=", description: _lt("is after or equal to") },
            { symbol: "<=", description: _lt("is before or equal to") },
            { symbol: "between", description: _lt("is between") },
            { symbol: "!=", description: _lt("is set"), value: false },
            { symbol: "=", description: _lt("is not set"), value: false },
        ],
        datetime: [
            { symbol: "between", description: _lt("is between") },
            { symbol: "=", description: _lt("is equal to") },
            { symbol: "!=", description: _lt("is not equal to") },
            { symbol: ">", description: _lt("is after") },
            { symbol: "<", description: _lt("is before") },
            { symbol: ">=", description: _lt("is after or equal to") },
            { symbol: "<=", description: _lt("is before or equal to") },
            { symbol: "!=", description: _lt("is set"), value: false },
            { symbol: "=", description: _lt("is not set"), value: false },
        ],
        id: [
            { symbol: "=", description:_lt("is")},
        ],
        number: [
            { symbol: "=", description: _lt("is equal to") },
            { symbol: "!=", description: _lt("is not equal to") },
            { symbol: ">", description: _lt("greater than") },
            { symbol: "<", description: _lt("less than") },
            { symbol: ">=", description: _lt("greater than or equal to") },
            { symbol: "<=", description: _lt("less than or equal to") },
            { symbol: "!=", description: _lt("is set"), value: false },
            { symbol: "=", description: _lt("is not set"), value: false },
        ],
        selection: [
            { symbol: "=", description:_lt("is")},
            { symbol: "!=", description: _lt("is not") },
            { symbol: "!=", description: _lt("is set"), value: false },
            { symbol: "=", description: _lt("is not set"), value: false },
        ],
    };
    const FIELD_TYPES = {
        boolean: 'boolean',
        char: 'char',
        date: 'date',
        datetime: 'datetime',
        float: 'number',
        id: 'id',
        integer: 'number',
        html: 'char',
        many2many: 'char',
        many2one: 'char',
        monetary: 'number',
        one2many: 'char',
        text: 'char',
        selection: 'selection',
    };
    const DEFAULT_PERIOD = 'this_month';
    const MONTH_OPTIONS = {
        this_month: { id: 'this_month', groupNumber: 1, format: 'MMMM', addParam: {}, setParam: {}, granularity: 'month' },
        last_month: { id: 'last_month', groupNumber: 1, format: 'MMMM', addParam: { months: -1 }, setParam: {}, granularity: 'month' },
        antepenultimate_month: { id: 'antepenultimate_month', groupNumber: 1, format: 'MMMM', addParam: { months: -2 }, setParam: {}, granularity: 'month' },
    };
    const QUARTER_OPTIONS = {
        fourth_quarter: { id: 'fourth_quarter', groupNumber: 1, description: _lt("Q4"), addParam: {}, setParam: { quarter: 4 }, granularity: 'quarter' },
        third_quarter: { id: 'third_quarter', groupNumber: 1, description: _lt("Q3"), addParam: {}, setParam: { quarter: 3 }, granularity: 'quarter' },
        second_quarter: { id: 'second_quarter', groupNumber: 1, description: _lt("Q2"), addParam: {}, setParam: { quarter: 2 }, granularity: 'quarter' },
        first_quarter: { id: 'first_quarter', groupNumber: 1, description: _lt("Q1"), addParam: {}, setParam: { quarter: 1 }, granularity: 'quarter' },
    };
    const YEAR_OPTIONS = {
        this_year: { id: 'this_year', groupNumber: 2, format: 'YYYY', addParam: {}, setParam: {}, granularity: 'year' },
        last_year: { id: 'last_year', groupNumber: 2, format: 'YYYY', addParam: { years: -1 }, setParam: {}, granularity: 'year' },
        antepenultimate_year: { id: 'antepenultimate_year', groupNumber: 2, format: 'YYYY', addParam: { years: -2 }, setParam: {}, granularity: 'year' },
    };
    const OPTION_GENERATORS = Object.assign({}, MONTH_OPTIONS, QUARTER_OPTIONS, YEAR_OPTIONS);

    // GroupBy menu parameters
    const GROUPABLE_TYPES = ['many2one', 'char', 'boolean', 'selection', 'date', 'datetime', 'integer'];
    const DEFAULT_INTERVAL = 'month';
    const INTERVAL_OPTIONS = {
        year: { description: _lt("Year"), id: 'year', groupNumber: 1 },
        quarter: { description: _lt("Quarter"), id: 'quarter', groupNumber: 1 },
        month: { description: _lt("Month"), id: 'month', groupNumber: 1 },
        week: { description: _lt("Week"), id: 'week', groupNumber: 1 },
        day: { description: _lt("Day"), id: 'day', groupNumber: 1 }
    };

    // TimeRange menu parameters
    const TIME_RANGE_OPTIONS = {
        last_7_days: { description: _lt("Last 7 Days"), id: 'last_7_days', groupNumber: 1 },
        last_30_days: { description: _lt("Last 30 Days"), id: 'last_30_days', groupNumber: 1 },
        last_365_days: { description: _lt("Last 365 Days"), id: 'last_365_days', groupNumber: 1 },
        last_5_years: { description: _lt("Last 5 Years"), id: 'last_5_years', groupNumber: 1 },
        today: { description: _lt("Today"), id: 'today', groupNumber: 2 },
        this_week: { description: _lt("This Week"), id: 'this_week', groupNumber: 2 },
        this_month: { description: _lt("This Month"), id: 'this_month', groupNumber: 2 },
        this_quarter: { description: _lt("This Quarter"), id: 'this_quarter', groupNumber: 2 },
        this_year: { description: _lt("This Year"), id: 'this_year', groupNumber: 2 },
        yesterday: { description: _lt("Yesterday"), id: 'yesterday', groupNumber: 3 },
        last_week: { description: _lt("Last Week"), id: 'last_week', groupNumber: 3 },
        last_month: { description: _lt("Last Month"), id: 'last_month', groupNumber: 3 },
        last_quarter: { description: _lt("Last Quarter"), id: 'last_quarter', groupNumber: 3 },
        last_year: { description: _lt("Last Year"), id: 'last_year', groupNumber: 3 },
    };
    const COMPARISON_TIME_RANGE_OPTIONS = {
        previous_period: { description: _lt("Previous Period"), id: 'previous_period' },
        previous_year: { description: _lt("Previous Year"), id: 'previous_year' },
    };

    // Search bar
    const FACET_ICONS = {
        filter: 'fa-filter',
        groupBy: 'fa-bars',
        favorite: 'fa-star',
        timeRange: 'fa-calendar',
    };

    /**
     * Construct a timeRange object from the given fieldName, rangeId, comparisonRangeId
     * parameters.
     *
     * @private
     * @param {string} filter.fieldName
     * @param {string} filter.rangeId
     * @param {string} filter.comparisonRangeId
     * @param {Object} fields
     */
    function extractTimeRange({ fieldName, rangeId, comparisonRangeId }, fields) {
        const field = fields[fieldName];
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
     *
     * @private
     * @param {Object} favorite
     * @param {string} action_id
     * @param {string} model_id
     * @returns {Object}
     */
    function favoriteToIrFilter(favorite, action_id, model_id) {
        const irFilter = { action_id, model_id };

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
     * Returns a filter of type 'favorite' starting from an ir_filter comming from db.
     *
     * @private
     * @param {Object} irFilter
     * @param {Object} params.userContext
     * @param {Object} [params.fields]
     * @returns {Object}
     */
    function irFilterToFavorite(irFilter, { userContext, fields }) {
        let userId = irFilter.user_id || false;
        if (Array.isArray(userId)) {
            userId = userId[0];
        }
        const groupNumber = userId ? 1 : 2;
        const context = pyUtils.eval('context', irFilter.context, userContext);
        let groupBys = [];
        if (context.group_by) {
            groupBys = context.group_by;
            delete context.group_by;
        }
        let timeRanges;
        if (fields && context.time_ranges) {
            const { field, range, comparisonRange } = context.time_ranges;
            timeRanges = extractTimeRange({
                fieldName: field,
                rangeId: range,
                comparisonRangeId: comparisonRange,
            }, fields);
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

    function rankInterval(oId) {
        return Object.keys(INTERVAL_OPTIONS).indexOf(oId);
    }

    function rankPeriod(oId) {
        return Object.keys(OPTION_GENERATORS).indexOf(oId);
    }

    return {
        COMPARISON_TIME_RANGE_OPTIONS,
        DEFAULT_INTERVAL,
        DEFAULT_PERIOD,
        FACET_ICONS,
        FIELD_OPERATORS,
        FIELD_TYPES,
        GROUPABLE_TYPES,
        INTERVAL_OPTIONS,
        OPTION_GENERATORS,
        TIME_RANGE_OPTIONS,
        YEAR_OPTIONS,

        extractTimeRange,
        favoriteToIrFilter,
        irFilterToFavorite,
        rankInterval,
        rankPeriod,
    };
});
