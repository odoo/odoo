odoo.define('web.searchUtils', function (require) {
    "use strict";

    const { _lt, _t } = require('web.core');
    const Domain = require('web.Domain');
    const pyUtils = require('web.py_utils');

    //-------------------------------------------------------------------------
    // Constants
    //-------------------------------------------------------------------------

    // Filter menu parameters
    const FIELD_OPERATORS = {
        binary: [
            { symbol: "!=", description: _lt("is set"), value: false },
            { symbol: "=", description: _lt("is not set"), value: false },
        ],
        boolean: [
            { symbol: "=", description: _lt("is true"), value: true },
            { symbol: "!=", description: _lt("is false"), value: true },
        ],
        char: [
            { symbol: "ilike", description: _lt("contains") },
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
            { symbol: "=", description: _lt("is") },
            { symbol: "<=", description: _lt("less than or equal to")},
            { symbol: ">", description: _lt("greater than")},
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
            { symbol: "=", description: _lt("is") },
            { symbol: "!=", description: _lt("is not") },
            { symbol: "!=", description: _lt("is set"), value: false },
            { symbol: "=", description: _lt("is not set"), value: false },
        ],
    };
    const FIELD_TYPES = {
        binary: 'binary',
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
    const QUARTERS = {
        1: { description: _lt("Q1"), coveredMonths: [0, 1, 2] },
        2: { description: _lt("Q2"), coveredMonths: [3, 4, 5] },
        3: { description: _lt("Q3"), coveredMonths: [6, 7, 8] },
        4: { description: _lt("Q4"), coveredMonths: [9, 10, 11] },
    };
    const MONTH_OPTIONS = {
        this_month: {
            id: 'this_month', groupNumber: 1, format: 'MMMM',
            addParam: {}, granularity: 'month',
        },
        last_month: {
            id: 'last_month', groupNumber: 1, format: 'MMMM',
            addParam: { months: -1 }, granularity: 'month',
        },
        antepenultimate_month: {
            id: 'antepenultimate_month', groupNumber: 1, format: 'MMMM',
            addParam: { months: -2 }, granularity: 'month',
        },
    };
    const QUARTER_OPTIONS = {
        fourth_quarter: {
            id: 'fourth_quarter', groupNumber: 1, description: QUARTERS[4].description,
            setParam: { quarter: 4 }, granularity: 'quarter',
        },
        third_quarter: {
            id: 'third_quarter', groupNumber: 1, description: QUARTERS[3].description,
            setParam: { quarter: 3 }, granularity: 'quarter',
        },
        second_quarter: {
            id: 'second_quarter', groupNumber: 1, description: QUARTERS[2].description,
            setParam: { quarter: 2 }, granularity: 'quarter',
        },
        first_quarter: {
            id: 'first_quarter', groupNumber: 1, description: QUARTERS[1].description,
            setParam: { quarter: 1 }, granularity: 'quarter',
        },
    };
    const YEAR_OPTIONS = {
        this_year: {
            id: 'this_year', groupNumber: 2, format: 'YYYY',
            addParam: {}, granularity: 'year',
        },
        last_year: {
            id: 'last_year', groupNumber: 2, format: 'YYYY',
            addParam: { years: -1 }, granularity: 'year',
        },
        antepenultimate_year: {
            id: 'antepenultimate_year', groupNumber: 2, format: 'YYYY',
            addParam: { years: -2 }, granularity: 'year',
        },
    };
    const PERIOD_OPTIONS = Object.assign({}, MONTH_OPTIONS, QUARTER_OPTIONS, YEAR_OPTIONS);

    // GroupBy menu parameters
    const GROUPABLE_TYPES = [
        'boolean',
        'char',
        'date',
        'datetime',
        'integer',
        'many2one',
        'many2many',
        'selection',
    ];
    const DEFAULT_INTERVAL = 'month';
    const INTERVAL_OPTIONS = {
        year: { description: _lt("Year"), id: 'year', groupNumber: 1 },
        quarter: { description: _lt("Quarter"), id: 'quarter', groupNumber: 1 },
        month: { description: _lt("Month"), id: 'month', groupNumber: 1 },
        week: { description: _lt("Week"), id: 'week', groupNumber: 1 },
        day: { description: _lt("Day"), id: 'day', groupNumber: 1 }
    };

    // Comparison menu parameters
    const COMPARISON_OPTIONS = {
        previous_period: {
            description: _lt("Previous Period"), id: 'previous_period',
        },
        previous_year: {
            description: _lt("Previous Year"), id: 'previous_year', addParam: { years: -1 },
        },
    };
    const PER_YEAR = {
        year: 1,
        quarter: 4,
        month: 12,
    };
    // Search bar
    const FACET_ICONS = {
        filter: 'fa fa-filter',
        groupBy: 'fa fa-bars',
        favorite: 'fa fa-star',
        comparison: 'fa fa-adjust',
    };

    //-------------------------------------------------------------------------
    // Functions
    //-------------------------------------------------------------------------

    /**
     * Constructs the string representation of a domain and its description. The
     * domain is of the form:
     *      ['|',..., '|', d_1,..., d_n]
     * where d_i is a time range of the form
     *      ['&', [fieldName, >=, leftBound_i], [fieldName, <=, rightBound_i]]
     * where leftBound_i and rightBound_i are date or datetime computed accordingly
     * to the given options and reference moment.
     * (@see constructDateRange).
     * @param {moment} referenceMoment
     * @param {string} fieldName
     * @param {string} fieldType
     * @param {string[]} selectedOptionIds
     * @param {string} [comparisonOptionId]
     * @returns {{ domain: string, description: string }}
     */
    function constructDateDomain(
        referenceMoment,
        fieldName,
        fieldType,
        selectedOptionIds,
        comparisonOptionId
    ) {
        let addParam;
        let selectedOptions;
        if (comparisonOptionId) {
            [addParam, selectedOptions] = getComparisonParams(
                referenceMoment,
                selectedOptionIds,
                comparisonOptionId);
        } else {
            selectedOptions = getSelectedOptions(referenceMoment, selectedOptionIds);
        }

        const yearOptions = selectedOptions.year;
        const otherOptions = [
            ...(selectedOptions.quarter || []),
            ...(selectedOptions.month || [])
        ];

        sortPeriodOptions(yearOptions);
        sortPeriodOptions(otherOptions);

        const ranges = [];
        for (const yearOption of yearOptions) {
            const constructRangeParams = {
                referenceMoment,
                fieldName,
                fieldType,
                addParam,
            };
            if (otherOptions.length) {
                for (const option of otherOptions) {
                    const setParam = Object.assign({},
                        yearOption.setParam,
                        option ? option.setParam : {}
                    );
                    const { granularity } = option;
                    const range = constructDateRange(Object.assign(
                        { granularity, setParam },
                        constructRangeParams
                    ));
                    ranges.push(range);
                }
            } else {
                const { granularity, setParam } = yearOption;
                const range = constructDateRange(Object.assign(
                    { granularity, setParam },
                    constructRangeParams
                ));
                ranges.push(range);
            }
        }

        const domain = pyUtils.assembleDomains(ranges.map(range => range.domain), 'OR');
        const description = ranges.map(range => range.description).join("/");

        return { domain, description };
    }

    /**
     * Constructs the string representation of a domain and its description. The
     * domain is a time range of the form:
     *      ['&', [fieldName, >=, leftBound],[fieldName, <=, rightBound]]
     * where leftBound and rightBound are some date or datetime determined by setParam,
     * addParam, granularity and the reference moment.
     * @param {Object} params
     * @param {moment} params.referenceMoment
     * @param {string} params.fieldName
     * @param {string} params.fieldType
     * @param {string} params.granularity
     * @param {Object} params.setParam
     * @param {Object} [params.addParam]
     * @returns {{ domain: string, description: string }}
     */
    function constructDateRange({
        referenceMoment,
        fieldName,
        fieldType,
        granularity,
        setParam,
        addParam,
    }) {
        const date = referenceMoment.clone().set(setParam).add(addParam || {});

        // compute domain
        let leftBound = date.clone().locale('en').startOf(granularity);
        let rightBound = date.clone().locale('en').endOf(granularity);
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

        // compute description
        const descriptions = [date.format("YYYY")];
        const method = _t.database.parameters.direction === "rtl" ? "push" : "unshift";
        if (granularity === "month") {
            descriptions[method](date.format("MMMM"));
        } else if (granularity === "quarter") {
            descriptions[method](QUARTERS[date.quarter()].description);
        }
        const description = descriptions.join(" ");

        return { domain, description, };
    }

    /**
     * Returns a version of the options in COMPARISON_OPTIONS with translated descriptions.
     * @see getOptionsWithDescriptions
     */
    function getComparisonOptions() {
        return getOptionsWithDescriptions(COMPARISON_OPTIONS);
    }

    /**
     * Returns the params addParam and selectedOptions necessary for the computation
     * of a comparison domain.
     * @param {moment} referenceMoment
     * @param {string{}} selectedOptionIds
     * @param {string} comparisonOptionId
     * @returns {Object[]}
     */
    function getComparisonParams(referenceMoment, selectedOptionIds, comparisonOptionId) {
        const comparisonOption = COMPARISON_OPTIONS[comparisonOptionId];
        const selectedOptions = getSelectedOptions(referenceMoment, selectedOptionIds);
        let addParam = comparisonOption.addParam;
        if (addParam) {
            return [addParam, selectedOptions];
        }
        addParam = {};

        let globalGranularity = 'year';
        if (selectedOptions.month) {
            globalGranularity = 'month';
        } else if (selectedOptions.quarter) {
            globalGranularity = 'quarter';
        }
        const granularityFactor = PER_YEAR[globalGranularity];
        const years = selectedOptions.year.map(o => o.setParam.year);
        const yearMin = Math.min(...years);
        const yearMax = Math.max(...years);

        let optionMin = 0;
        let optionMax = 0;
        if (selectedOptions.quarter) {
            const quarters = selectedOptions.quarter.map(o => o.setParam.quarter);
            if (globalGranularity === 'month') {
                delete selectedOptions.quarter;
                for (const quarter of quarters) {
                    for (const month of QUARTERS[quarter].coveredMonths) {
                        const monthOption = selectedOptions.month.find(
                            o => o.setParam.month === month
                        );
                        if (!monthOption) {
                            selectedOptions.month.push({
                                setParam: { month, }, granularity: 'month',
                            });
                        }
                    }
                }
            } else {
                optionMin = Math.min(...quarters);
                optionMax = Math.max(...quarters);
            }
        }
        if (selectedOptions.month) {
            const months = selectedOptions.month.map(o => o.setParam.month);
            optionMin = Math.min(...months);
            optionMax = Math.max(...months);
        }

        addParam[globalGranularity] = -1 +
            granularityFactor * (yearMin - yearMax) +
            optionMin - optionMax;

        return [addParam, selectedOptions];
    }

    /**
     * Returns a version of the options in INTERVAL_OPTIONS with translated descriptions.
     * @see getOptionsWithDescriptions
     */
    function getIntervalOptions() {
        return getOptionsWithDescriptions(INTERVAL_OPTIONS);
    }

    /**
     * Returns a version of the options in PERIOD_OPTIONS with translated descriptions
     * and a key defautlYearId used in the control panel model when toggling a period option.
     * @param {moment} referenceMoment
     * @returns {Object[]}
     */
    function getPeriodOptions(referenceMoment) {
        const options = [];
        for (const option of Object.values(PERIOD_OPTIONS)) {
            const { id, groupNumber, description, } = option;
            const res = { id, groupNumber, };
            const date = referenceMoment.clone().set(option.setParam).add(option.addParam);
            if (description) {
                res.description = description.toString();
            } else {
                res.description = date.format(option.format.toString());
            }
            res.setParam = getSetParam(option, referenceMoment);
            res.defaultYear = date.year();
            options.push(res);
        }
        for (const option of options) {
            const yearOption = options.find(
                o => o.setParam && o.setParam.year === option.defaultYear
            );
            option.defaultYearId = yearOption.id;
            delete option.defaultYear;
            delete option.setParam;
        }
        return options;
    }

    /**
     * Returns a version of the options in OPTIONS with translated descriptions (if any).
     * @param {Object{}} OPTIONS
     * @returns {Object[]}
     */
    function getOptionsWithDescriptions(OPTIONS) {
        const options = [];
        for (const option of Object.values(OPTIONS)) {
            const { id, groupNumber, description, } = option;
            const res = { id, };
            if (description) {
                res.description = description.toString();
            }
            if (groupNumber) {
                res.groupNumber = groupNumber;
            }
            options.push(res);
        }
        return options;
    }

    /**
     * Returns a version of the period options whose ids are in selectedOptionIds
     * partitioned by granularity.
     * @param {moment} referenceMoment
     * @param {string[]} selectedOptionIds
     * @param {Object}
     */
    function getSelectedOptions(referenceMoment, selectedOptionIds) {
        const selectedOptions = { year: [] };
        for (const optionId of selectedOptionIds) {
            const option = PERIOD_OPTIONS[optionId];
            const setParam = getSetParam(option, referenceMoment);
            const granularity = option.granularity;
            if (!selectedOptions[granularity]) {
                selectedOptions[granularity] = [];
            }
            selectedOptions[granularity].push({ granularity, setParam });
        }
        return selectedOptions;
    }

    /**
     * Returns the setParam object associated with the given periodOption and
     * referenceMoment.
     * @param {Object} periodOption
     * @param {moment} referenceMoment
     * @returns {Object}
     */
    function getSetParam(periodOption, referenceMoment) {
        if (periodOption.setParam) {
            return periodOption.setParam;
        }
        const date = referenceMoment.clone().add(periodOption.addParam);
        const setParam = {};
        setParam[periodOption.granularity] = date[periodOption.granularity]();
        return setParam;
    }

    /**
     * @param {string} intervalOptionId
     * @returns {number} index
     */
    function rankInterval(intervalOptionId) {
        return Object.keys(INTERVAL_OPTIONS).indexOf(intervalOptionId);
    }

    /**
     * Sorts in place an array of 'period' options.
     * @param {Object[]} options supposed to be of the form:
     *                                      { granularity, setParam, }
     */
    function sortPeriodOptions(options) {
        options.sort((o1, o2) => {
            const granularity1 = o1.granularity;
            const granularity2 = o2.granularity;
            if (granularity1 === granularity2) {
                return o1.setParam[granularity1] - o2.setParam[granularity1];
            }
            return granularity1 < granularity2 ? -1 : 1;
        });
    }

    /**
     * Checks if a year id is among the given array of period option ids.
     * @param {string[]} selectedOptionIds
     * @returns {boolean}
     */
    function yearSelected(selectedOptionIds) {
        return selectedOptionIds.some(optionId => !!YEAR_OPTIONS[optionId]);
    }

    return {
        COMPARISON_OPTIONS,
        DEFAULT_INTERVAL,
        DEFAULT_PERIOD,
        FACET_ICONS,
        FIELD_OPERATORS,
        FIELD_TYPES,
        GROUPABLE_TYPES,
        INTERVAL_OPTIONS,
        PERIOD_OPTIONS,

        constructDateRange,
        constructDateDomain,
        getComparisonOptions,
        getIntervalOptions,
        getPeriodOptions,
        rankInterval,
        yearSelected,
    };
});
