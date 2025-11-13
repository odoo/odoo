import { globalFilterDateRegistry } from "@spreadsheet/global_filters/helpers";
import { _t } from "@web/core/l10n/translation";

globalFilterDateRegistry
    .add("this_fiscal_year", {
        sequence: 155,
        label: _t("Current Fiscal Year"),
        canOnlyBeDefault: true,
        getDefaultValue: (now) => ({ type: "fiscal_year", offset: 0 }),
        category: "fiscal_year",
        shouldBeHidden: (getters) => isFiscalYearSameAsStandardYear(getters),
    })
    .add("fiscal_year", {
        sequence: 156,
        label: _t("Fiscal Year"),
        getDateRange: (now, value, dataSourceOffset, getters) => {
            const offset = (value?.offset ?? 0) + dataSourceOffset;
            return getFiscalYearFromTo(offset, getters);
        },
        getNextDateFilterValue: (value) => ({
            type: "fiscal_year",
            offset: value.offset + 1,
        }),
        getPreviousDateFilterValue: (value) => ({
            type: "fiscal_year",
            offset: value.offset - 1,
        }),
        isValueValid: (value) => Number.isInteger(value.offset),
        getValueString: (value, getters) => getFiscalYearDisplayString(value, getters),
        isFixedPeriod: true,
        getCurrentFixedPeriod: (now) => ({ type: "fiscal_year", offset: 0 }),
        category: "fiscal_year",
        shouldBeHidden: (getters) => isFiscalYearSameAsStandardYear(getters),
    });

function getFiscalYearFromTo(offset, getters) {
    const currentFiscalYearStart = getters.getCurrentFiscalYearStart();
    const currentFiscalYearEnd = getters.getCurrentFiscalYearEnd();
    const start = currentFiscalYearStart.plus({ years: offset }).startOf("day");
    const end = currentFiscalYearEnd.plus({ years: offset }).endOf("day");
    return { from: start, to: end };
}

function getFiscalYearDisplayString(value, getters) {
    const { from, to } = getFiscalYearFromTo(value.offset || 0, getters);
    return from.year === to.year ? String(from.year) : String(from.year) + "-" + String(to.year);
}

function isFiscalYearSameAsStandardYear(getters) {
    const fiscalYearStart = getters.getCurrentFiscalYearStart();
    const fiscalYearEnd = getters.getCurrentFiscalYearEnd();
    return (
        fiscalYearStart.month === 1 &&
        fiscalYearStart.day === 1 &&
        fiscalYearEnd.month === 12 &&
        fiscalYearEnd.day === 31
    );
}
