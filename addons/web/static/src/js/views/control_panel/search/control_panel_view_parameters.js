odoo.define('web.controlPanelViewParameters', function (require) {
"use strict";

var core = require('web.core');

var _lt = core._lt;

// for FilterMenu
const DEFAULT_PERIOD = 'this_month';
const PERIOD_OPTIONS = [
    { description: _lt('Last 7 Days'), optionId: 'last_7_days', groupId: 1 },
    { description: _lt('Last 30 Days'), optionId: 'last_30_days', groupId: 1 },
    { description: _lt('Last 365 Days'), optionId: 'last_365_days', groupId: 1 },
    { description: _lt('Last 5 Years'), optionId: 'last_5_years', groupId: 1 },
    { description: _lt('Today'), optionId: 'today', groupId: 2 },
    { description: _lt('This Week'), optionId: 'this_week', groupId: 2 },
    { description: _lt('This Month'), optionId: 'this_month', groupId: 2 },
    { description: _lt('This Quarter'), optionId: 'this_quarter', groupId: 2 },
    { description: _lt('This Year'), optionId: 'this_year', groupId: 2 },
    { description: _lt('Yesterday'), optionId: 'yesterday', groupId: 3 },
    { description: _lt('Last Week'), optionId: 'last_week', groupId: 3 },
    { description: _lt('Last Month'), optionId: 'last_month', groupId: 3 },
    { description: _lt('Last Quarter'), optionId: 'last_quarter', groupId: 3 },
    { description: _lt('Last Year'), optionId: 'last_year', groupId: 3 },
];
const MONTH_OPTIONS = [
    { optionId: 'this_month', groupId: 1, format: 'MMMM', addParam: {}, setParam: {}, granularity: 'month' },
    { optionId: 'last_month', groupId: 1, format: 'MMMM', addParam: { months: -1 }, setParam: {}, granularity: 'month' },
    { optionId: 'antepenultimate_month', groupId: 1, format: 'MMMM', addParam: { months: -2 }, setParam: {}, granularity: 'month' }
]
const QUARTER_OPTIONS = [
    { optionId: 'fourth_quarter', groupId: 1, description: _lt("Q4"), addParam: {}, setParam: { quarter: 4 }, granularity: 'quarter' },
    { optionId: 'third_quarter', groupId: 1, description: _lt("Q3"), addParam: {}, setParam: { quarter: 3 }, granularity: 'quarter' },
    { optionId: 'second_quarter', groupId: 1, description: _lt("Q2"), addParam: {}, setParam: { quarter: 2 }, granularity: 'quarter' },
    { optionId: 'first_quarter', groupId: 1, description: _lt("Q1"), addParam: {}, setParam: { quarter: 1 }, granularity: 'quarter' }
]
const YEAR_OPTIONS = [
    { optionId: 'this_year', groupId: 2, format: 'YYYY', addParam: {}, setParam: {}, granularity: 'year' },
    { optionId: 'last_year', groupId: 2, format: 'YYYY', addParam: { years: -1 }, setParam: {}, granularity: 'year' },
    { optionId: 'antepenultimate_year', groupId: 2, format: 'YYYY', addParam: { years: -2 }, setParam: {}, granularity: 'year' },
];
const OPTION_GENERATORS =  [...MONTH_OPTIONS, ...QUARTER_OPTIONS, ...YEAR_OPTIONS];

// for GroupBy menu
const GROUPABLE_TYPES = ['many2one', 'char', 'boolean', 'selection', 'date', 'datetime', 'integer'];
const DEFAULT_INTERVAL = 'month';
const INTERVAL_OPTIONS = [
    { description: _lt('Year'), optionId: 'year', groupId: 1 },
    { description: _lt('Quarter'), optionId: 'quarter', groupId: 1 },
    { description: _lt('Month'), optionId: 'month', groupId: 1 },
    { description: _lt('Week'), optionId: 'week', groupId: 1 },
    { description: _lt('Day'), optionId: 'day', groupId: 1 },
];

// for TimeRangeMenu
const DEFAULT_TIMERANGE = DEFAULT_PERIOD;
const TIME_RANGE_OPTIONS = PERIOD_OPTIONS;
const COMPARISON_TIME_RANGE_OPTIONS = [
    { description: _lt('Previous Period'), optionId: 'previous_period' },
    { description: _lt('Previous Year'), optionId: 'previous_year' }
];

return {
    COMPARISON_TIME_RANGE_OPTIONS: COMPARISON_TIME_RANGE_OPTIONS,
    DEFAULT_INTERVAL: DEFAULT_INTERVAL,
    DEFAULT_PERIOD: DEFAULT_PERIOD,
    DEFAULT_TIMERANGE: DEFAULT_TIMERANGE,
    GROUPABLE_TYPES: GROUPABLE_TYPES,
    INTERVAL_OPTIONS: INTERVAL_OPTIONS,
    OPTION_GENERATORS: OPTION_GENERATORS,
    PERIOD_OPTIONS: PERIOD_OPTIONS,
    TIME_RANGE_OPTIONS: TIME_RANGE_OPTIONS,
    YEAR_OPTIONS: YEAR_OPTIONS,
};

});