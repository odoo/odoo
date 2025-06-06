import { Range, RangeData } from "@odoo/o-spreadsheet";
import { DomainListRepr } from "@web/core/domain";

declare module "@spreadsheet" {
    export type RangeType = "fixedPeriod" | "relative" | "from_to";
    export type FixedPeriods = "quarter" | "month";
    export type RelativePeriod =
        | "last_7_days"
        | "last_30_days"
        | "last_90_days"
        | "last_12_months"
        | "year_to_date";

    export type DateFilterTimePeriod = RelativePeriod | "this_month" | "this_quarter" | "this_year";

    export interface FieldMatching {
        chain: string;
        type: string;
        offset?: number;
    }

    export interface TextGlobalFilter {
        type: "text";
        id: string;
        label: string;
        rangesOfAllowedValues?: Range[];
        defaultValue?: string[];
    }

    export interface CmdTextGlobalFilter extends TextGlobalFilter {
        rangesOfAllowedValues?: RangeData[];
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
        defaultValue?: DateFilterTimePeriod;
    }

    export interface FixedPeriodDateGlobalFilter extends DateGlobalFilterCommon {
        rangeType: "fixedPeriod";
        defaultValue?: "this_month" | "this_quarter" | "this_year";
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
