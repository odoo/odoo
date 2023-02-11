/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";

export const DEFAULT_PERIOD = "this_month";

export const QUARTERS = {
    1: { description: _lt("Q1"), coveredMonths: [1, 2, 3] },
    2: { description: _lt("Q2"), coveredMonths: [4, 5, 6] },
    3: { description: _lt("Q3"), coveredMonths: [7, 8, 9] },
    4: { description: _lt("Q4"), coveredMonths: [10, 11, 12] },
};

export const MONTH_OPTIONS = {
    this_month: {
        id: "this_month",
        groupNumber: 1,
        format: "MMMM",
        plusParam: {},
        granularity: "month",
    },
    last_month: {
        id: "last_month",
        groupNumber: 1,
        format: "MMMM",
        plusParam: { months: -1 },
        granularity: "month",
    },
    antepenultimate_month: {
        id: "antepenultimate_month",
        groupNumber: 1,
        format: "MMMM",
        plusParam: { months: -2 },
        granularity: "month",
    },
};

export const QUARTER_OPTIONS = {
    fourth_quarter: {
        id: "fourth_quarter",
        groupNumber: 1,
        description: QUARTERS[4].description,
        setParam: { quarter: 4 },
        granularity: "quarter",
    },
    third_quarter: {
        id: "third_quarter",
        groupNumber: 1,
        description: QUARTERS[3].description,
        setParam: { quarter: 3 },
        granularity: "quarter",
    },
    second_quarter: {
        id: "second_quarter",
        groupNumber: 1,
        description: QUARTERS[2].description,
        setParam: { quarter: 2 },
        granularity: "quarter",
    },
    first_quarter: {
        id: "first_quarter",
        groupNumber: 1,
        description: QUARTERS[1].description,
        setParam: { quarter: 1 },
        granularity: "quarter",
    },
};

export const YEAR_OPTIONS = {
    this_year: {
        id: "this_year",
        groupNumber: 2,
        format: "yyyy",
        plusParam: {},
        granularity: "year",
    },
    last_year: {
        id: "last_year",
        groupNumber: 2,
        format: "yyyy",
        plusParam: { years: -1 },
        granularity: "year",
    },
    antepenultimate_year: {
        id: "antepenultimate_year",
        groupNumber: 2,
        format: "yyyy",
        plusParam: { years: -2 },
        granularity: "year",
    },
};

export const PERIOD_OPTIONS = Object.assign({}, MONTH_OPTIONS, QUARTER_OPTIONS, YEAR_OPTIONS);

export const DEFAULT_INTERVAL = "month";

export const INTERVAL_OPTIONS = {
    year: { description: _lt("Year"), id: "year", groupNumber: 1 },
    quarter: { description: _lt("Quarter"), id: "quarter", groupNumber: 1 },
    month: { description: _lt("Month"), id: "month", groupNumber: 1 },
    week: { description: _lt("Week"), id: "week", groupNumber: 1 },
    day: { description: _lt("Day"), id: "day", groupNumber: 1 },
};

// ComparisonMenu parameters
export const COMPARISON_OPTIONS = {
    previous_period: {
        description: _lt("Previous Period"),
        id: "previous_period",
    },
    previous_year: {
        description: _lt("Previous Year"),
        id: "previous_year",
        plusParam: { years: -1 },
    },
};

export const PER_YEAR = {
    year: 1,
    quarter: 4,
    month: 12,
};

//-------------------------------------------------------------------------
// Functions
//-------------------------------------------------------------------------

/**
 * Constructs the string representation of a domain and its description. The
 * domain is of the form:
 *      ['|', d_1 ,..., '|', d_n]
 * where d_i is a time range of the form
 *      ['&', [fieldName, >=, leftBound_i], [fieldName, <=, rightBound_i]]
 * where leftBound_i and rightBound_i are date or datetime computed accordingly
 * to the given options and reference moment.
 */
export function constructDateDomain(
    referenceMoment,
    fieldName,
    fieldType,
    selectedOptionIds,
    comparisonOptionId
) {
    let plusParam;
    let selectedOptions;
    if (comparisonOptionId) {
        [plusParam, selectedOptions] = getComparisonParams(
            referenceMoment,
            selectedOptionIds,
            comparisonOptionId
        );
    } else {
        selectedOptions = getSelectedOptions(referenceMoment, selectedOptionIds);
    }
    const yearOptions = selectedOptions.year;
    const otherOptions = [...(selectedOptions.quarter || []), ...(selectedOptions.month || [])];
    sortPeriodOptions(yearOptions);
    sortPeriodOptions(otherOptions);
    const ranges = [];
    for (const yearOption of yearOptions) {
        const constructRangeParams = {
            referenceMoment,
            fieldName,
            fieldType,
            plusParam,
        };
        if (otherOptions.length) {
            for (const option of otherOptions) {
                const setParam = Object.assign(
                    {},
                    yearOption.setParam,
                    option ? option.setParam : {}
                );
                const { granularity } = option;
                const range = constructDateRange(
                    Object.assign({ granularity, setParam }, constructRangeParams)
                );
                ranges.push(range);
            }
        } else {
            const { granularity, setParam } = yearOption;
            const range = constructDateRange(
                Object.assign({ granularity, setParam }, constructRangeParams)
            );
            ranges.push(range);
        }
    }
    const domain = Domain.combine(
        ranges.map((range) => range.domain),
        "OR"
    );
    const description = ranges.map((range) => range.description).join("/");
    return { domain, description };
}

/**
 * Constructs the string representation of a domain and its description. The
 * domain is a time range of the form:
 *      ['&', [fieldName, >=, leftBound],[fieldName, <=, rightBound]]
 * where leftBound and rightBound are some date or datetime determined by setParam,
 * plusParam, granularity and the reference moment.
 */
export function constructDateRange(params) {
    const { referenceMoment, fieldName, fieldType, granularity, setParam, plusParam } = params;
    if ("quarter" in setParam) {
        // Luxon does not consider quarter key in setParam (like moment did)
        setParam.month = QUARTERS[setParam.quarter].coveredMonths[0];
        delete setParam.quarter;
    }
    const date = referenceMoment.set(setParam).plus(plusParam || {});
    // compute domain
    const leftDate = date.startOf(granularity);
    const rightDate = date.endOf(granularity);
    let leftBound;
    let rightBound;
    if (fieldType === "date") {
        leftBound = serializeDate(leftDate);
        rightBound = serializeDate(rightDate);
    } else {
        leftBound = serializeDateTime(leftDate);
        rightBound = serializeDateTime(rightDate);
    }
    const domain = new Domain(["&", [fieldName, ">=", leftBound], [fieldName, "<=", rightBound]]);
    // compute description
    const descriptions = [date.toFormat("yyyy")];
    const method = localization.direction === "rtl" ? "push" : "unshift";
    if (granularity === "month") {
        descriptions[method](date.toFormat("MMMM"));
    } else if (granularity === "quarter") {
        const quarter = date.quarter;
        descriptions[method](QUARTERS[quarter].description.toString());
    }
    const description = descriptions.join(" ");
    return { domain, description };
}

/**
 * Returns a version of the options in COMPARISON_OPTIONS with translated descriptions.
 * @see getOptionsWithDescriptions
 */
export function getComparisonOptions() {
    return getOptionsWithDescriptions(COMPARISON_OPTIONS);
}

/**
 * Returns the params plusParam and selectedOptions necessary for the computation
 * of a comparison domain.
 */
export function getComparisonParams(referenceMoment, selectedOptionIds, comparisonOptionId) {
    const comparisonOption = COMPARISON_OPTIONS[comparisonOptionId];
    const selectedOptions = getSelectedOptions(referenceMoment, selectedOptionIds);
    if (comparisonOption.plusParam) {
        return [comparisonOption.plusParam, selectedOptions];
    }
    const plusParam = {};
    let globalGranularity = "year";
    if (selectedOptions.month) {
        globalGranularity = "month";
    } else if (selectedOptions.quarter) {
        globalGranularity = "quarter";
    }
    const granularityFactor = PER_YEAR[globalGranularity];
    const years = selectedOptions.year.map((o) => o.setParam.year);
    const yearMin = Math.min(...years);
    const yearMax = Math.max(...years);
    let optionMin = 0;
    let optionMax = 0;
    if (selectedOptions.quarter) {
        const quarters = selectedOptions.quarter.map((o) => o.setParam.quarter);
        if (globalGranularity === "month") {
            delete selectedOptions.quarter;
            for (const quarter of quarters) {
                for (const month of QUARTERS[quarter].coveredMonths) {
                    const monthOption = selectedOptions.month.find(
                        (o) => o.setParam.month === month
                    );
                    if (!monthOption) {
                        selectedOptions.month.push({
                            setParam: { month },
                            granularity: "month",
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
        const months = selectedOptions.month.map((o) => o.setParam.month);
        optionMin = Math.min(...months);
        optionMax = Math.max(...months);
    }
    const num = -1 + granularityFactor * (yearMin - yearMax) + optionMin - optionMax;
    const key =
        globalGranularity === "year"
            ? "years"
            : globalGranularity === "month"
            ? "months"
            : "quarters";
    plusParam[key] = num;
    return [plusParam, selectedOptions];
}

/**
 * Returns a version of the options in INTERVAL_OPTIONS with translated descriptions.
 * @see getOptionsWithDescriptions
 */
export function getIntervalOptions() {
    return getOptionsWithDescriptions(INTERVAL_OPTIONS);
}

/**
 * Returns a version of the options in PERIOD_OPTIONS with translated descriptions
 * and a key defautlYearId used in the control panel model when toggling a period option.
 */
export function getPeriodOptions(referenceMoment) {
    // adapt when solution for moment is found...
    const options = [];
    const originalOptions = Object.values(PERIOD_OPTIONS);
    for (const option of originalOptions) {
        const { id, groupNumber } = option;
        let description;
        let defaultYear;
        switch (option.granularity) {
            case "quarter":
                description = option.description.toString();
                defaultYear = referenceMoment.set(option.setParam).year;
                break;
            case "month":
            case "year":
                const date = referenceMoment.plus(option.plusParam);
                description = date.toFormat(option.format);
                defaultYear = date.year;
                break;
        }
        const setParam = getSetParam(option, referenceMoment);
        options.push({ id, groupNumber, description, defaultYear, setParam });
    }
    const periodOptions = [];
    for (const option of options) {
        const { id, groupNumber, description, defaultYear } = option;
        const yearOption = options.find((o) => o.setParam && o.setParam.year === defaultYear);
        periodOptions.push({
            id,
            groupNumber,
            description,
            defaultYearId: yearOption.id,
        });
    }
    return periodOptions;
}

/**
 * Returns a version of the options in OPTIONS with translated descriptions (if any).
 * @param {Object{}} OPTIONS
 * @returns {Object[]}
 */
export function getOptionsWithDescriptions(OPTIONS) {
    const options = [];
    for (const option of Object.values(OPTIONS)) {
        options.push(Object.assign({}, option, { description: option.description.toString() }));
    }
    return options;
}

/**
 * Returns a partial version of the period options whose ids are in selectedOptionIds
 * partitioned by granularity.
 */
export function getSelectedOptions(referenceMoment, selectedOptionIds) {
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
 */
export function getSetParam(periodOption, referenceMoment) {
    if (periodOption.granularity === "quarter") {
        return periodOption.setParam;
    }
    const date = referenceMoment.plus(periodOption.plusParam);
    const granularity = periodOption.granularity;
    const setParam = { [granularity]: date[granularity] };
    return setParam;
}

export function rankInterval(intervalOptionId) {
    return Object.keys(INTERVAL_OPTIONS).indexOf(intervalOptionId);
}

/**
 * Sorts in place an array of 'period' options.
 */
export function sortPeriodOptions(options) {
    options.sort((o1, o2) => {
        var _a, _b;
        const granularity1 = o1.granularity;
        const granularity2 = o2.granularity;
        if (granularity1 === granularity2) {
            return (
                ((_a = o1.setParam[granularity1]) !== null && _a !== void 0 ? _a : 0) -
                ((_b = o2.setParam[granularity1]) !== null && _b !== void 0 ? _b : 0)
            );
        }
        return granularity1 < granularity2 ? -1 : 1;
    });
}

/**
 * Checks if a year id is among the given array of period option ids.
 */
export function yearSelected(selectedOptionIds) {
    return selectedOptionIds.some((optionId) => Object.keys(YEAR_OPTIONS).includes(optionId));
}
