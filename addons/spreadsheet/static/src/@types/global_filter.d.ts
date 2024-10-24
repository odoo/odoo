import { Range, RangeData } from "@odoo/o-spreadsheet";
import { DomainListRepr } from "@web/core/domain";

declare module "@spreadsheet" {
    export type RangeType = "fixedPeriod" | "relative" | "from_to";
    export type FixedPeriods = "quarter" | "month";
    export type RelativeUnit =
        | "day"
        | "week_to_date"
        | "week"
        | "month_to_date"
        | "month"
        | "quarter"
        | "year_to_date"
        | "year";

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
        defaultValue?: number[];
    }

    export interface RelativeDateGlobalFilter extends DateGlobalFilterCommon {
        rangeType: "relative";
        defaultValue?: RelativeDateValue;
    }

    export interface RelativeDateValue {
        reference: "this" | "next" | "previous";
        unit: RelativeUnit;
        interval?: number; // number of days, weeks, months, or years (undefined for "this")
    }

    export interface FixedPeriodDateGlobalFilter extends DateGlobalFilterCommon {
        rangeType: "fixedPeriod";
        defaultValue?: { period?: string; yearOffset?: number };
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
        domainOfAllowedValues?: DomainListRepr | string;
    }

    export type GlobalFilter = TextGlobalFilter | DateGlobalFilter | RelationalGlobalFilter;
    export type CmdGlobalFilter = CmdTextGlobalFilter | DateGlobalFilter | RelationalGlobalFilter;
}
