import { Range, RangeData } from "@odoo/o-spreadsheet";

declare module "@spreadsheet" {
    export type RangeType = "fixedPeriod" | "relative" | "from_to";
    export type RelativePeriod =
        | "last_month"
        | "last_week"
        | "last_three_months"
        | "last_six_months"
        | "last_year"
        | "last_three_years"
        | "year_to_date";
    export type DateFilterAutomaticPeriod = "this_month" | "this_quarter" | "this_year";
    export type DateFilterTimePeriod = RelativePeriod | DateFilterAutomaticPeriod;

    export interface FieldMatching {
        chain: string;
        type: string;
        offset?: number;
    }

    export interface TextGlobalFilter {
        type: "text";
        id: string;
        label: string;
        rangeOfAllowedValues?: Range;
        defaultValue?: string;
    }

    export interface CmdTextGlobalFilter extends TextGlobalFilter {
        rangeOfAllowedValues?: RangeData;
    }

    export interface DateGlobalFilterCommon {
        type: "date";
        id: string;
        label: string;
    }

    export interface FromToDateGlobalFilter extends DateGlobalFilterCommon {
        rangeType: "from_to";
        defaultValue?: { from?: string; to?: string };
    }

    export interface RelativeDateGlobalFilter extends DateGlobalFilterCommon {
        rangeType: "relative";
        defaultValue?: RelativePeriod;
    }

    export interface FixedPeriodDateGlobalFilter extends DateGlobalFilterCommon {
        rangeType: "fixedPeriod";
        defaultValue?: { period?: string; yearOffset?: number } | DateFilterAutomaticPeriod;
        disabledPeriods?: FixedPeriods[];
    }

    export type DateGlobalFilter =
        | FromToDateGlobalFilter
        | RelativeDateGlobalFilter
        | FixedPeriodDateGlobalFilter;

    export interface RelationalGlobalFilter {
        type: "relation";
        id: string;
        label: string;
        modelName: string;
        includeChildren: boolean;
        defaultValue?: "current_user" | number[];
        defaultValueDisplayNames: string[];
    }

    export type GlobalFilter = TextGlobalFilter | DateGlobalFilter | RelationalGlobalFilter;
    export type CmdGlobalFilter = CmdTextGlobalFilter | DateGlobalFilter | RelationalGlobalFilter;

    export type FixedPeriods = "quarter" | "month";
}
