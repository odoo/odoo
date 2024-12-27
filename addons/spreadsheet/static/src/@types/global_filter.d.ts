import { Range, RangeData } from "@odoo/o-spreadsheet";
import { DomainListRepr } from "@web/core/domain";

declare module "@spreadsheet" {
    export type RangeType = "fixedPeriod" | "relative" | "from_to";
    export type FixedPeriods = "quarter" | "month";
    export type RelativePeriod =
        | "last_month"
        | "last_week"
        | "last_three_months"
        | "last_six_months"
        | "last_year"
        | "last_three_years"
        | "year_to_date";
    export type DateFilterTimePeriod = RelativePeriod | "this_month" | "this_quarter" | "this_year";

    export interface FieldMatching {
        chain: string;
        type: string;
        offset?: number;
    }

    export interface TextGlobalFilter {
        id: string;
        operator: "ilike";
        label: string;
        rangeOfAllowedValues?: Range;
        defaultValue?: string;
    }

    export interface CmdTextGlobalFilter extends TextGlobalFilter {
        rangeOfAllowedValues?: RangeData;
    }

    export interface DateGlobalFilterCommon {
        id: string;
        label: string;
    }

    export interface FromToDateGlobalFilter extends DateGlobalFilterCommon {
        operator: "from_to";
        defaultValue?: number[];
    }

    export interface RelativeDateGlobalFilter extends DateGlobalFilterCommon {
        operator: "relative";
        defaultValue?: DateFilterTimePeriod;
    }

    export interface FixedPeriodDateGlobalFilter extends DateGlobalFilterCommon {
        operator: "fixedPeriod";
        defaultValue?: { period?: string; yearOffset?: number };
        disabledPeriods?: FixedPeriods[];
    }

    export type DateGlobalFilter =
        | FromToDateGlobalFilter
        | RelativeDateGlobalFilter
        | FixedPeriodDateGlobalFilter;

    export interface RelationalGlobalFilter {
        id: string;
        label: string;
        relation: string;
        operator: "in" | "child_of";
        defaultValue?: (number | "uid")[];
        domainOfAllowedValues?: DomainListRepr | string;
    }

    export type GlobalFilter = TextGlobalFilter | DateGlobalFilter | RelationalGlobalFilter;
    export type CmdGlobalFilter = CmdTextGlobalFilter | DateGlobalFilter | RelationalGlobalFilter;
}
