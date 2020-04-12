odoo.define('web.searchUtils', function (require) {
    "use strict";

    const { _lt } = require('web.core');

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

    function rankPeriod(oId) {
        return Object.keys(OPTION_GENERATORS).indexOf(oId);
    }

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
    function rankInterval(oId) {
        return Object.keys(INTERVAL_OPTIONS).indexOf(oId);
    }

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

        rankInterval,
        rankPeriod,
    };
});
