import { Range, RangeData } from "@odoo/o-spreadsheet";
import { DomainListRepr } from "@web/core/domain";

declare module "@spreadsheet" {
    export type DateDefaultValue =
        | "today"
        | "yesterday"
        | "last_7_days"
        | "last_30_days"
        | "last_90_days"
        | "month_to_date"
        | "last_month"
        | "this_month"
        | "this_quarter"
        | "last_12_months"
        | "this_year"
        | "year_to_date";

    export interface MonthDateValue {
        type: "month";
        year: number;
        month: number; // 1-12
    }

    export interface QuarterDateValue {
        type: "quarter";
        year: number;
        quarter: number; // 1-4
    }

    export interface YearDateValue {
        type: "year";
        year: number;
    }

    export interface RelativeDateValue {
        type: "relative";
        period:
            | "today"
            | "yesterday"
            | "last_7_days"
            | "last_30_days"
            | "last_90_days"
            | "month_to_date"
            | "last_month"
            | "last_12_months"
            | "year_to_date";
    }

    export interface DateRangeValue {
        type: "range";
        from?: string;
        to?: string;
    }

    export type DateValue =
        | MonthDateValue
        | QuarterDateValue
        | YearDateValue
        | RelativeDateValue
        | DateRangeValue;

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

    export interface SelectionGlobalFilter {
        type: "selection";
        id: string;
        label: string;
        resModel: string;
        selectionField: string;
        defaultValue?: string[];
    }

    export interface CmdTextGlobalFilter extends TextGlobalFilter {
        rangesOfAllowedValues?: RangeData[];
    }

    export interface DateGlobalFilter {
        type: "date";
        id: string;
        label: string;
        defaultValue?: DateDefaultValue;
    }

    export interface RelationalGlobalFilter {
        type: "relation";
        id: string;
        label: string;
        modelName: string;
        includeChildren: boolean;
        defaultValue?: "current_user" | number[];
        domainOfAllowedValues?: DomainListRepr | string;
    }

    export interface BooleanGlobalFilter {
        type: "boolean";
        id: string;
        label: string;
        defaultValue?: boolean[];
    }

    export type GlobalFilter = TextGlobalFilter | DateGlobalFilter | RelationalGlobalFilter | BooleanGlobalFilter | SelectionGlobalFilter;
    export type CmdGlobalFilter = CmdTextGlobalFilter | DateGlobalFilter | RelationalGlobalFilter | BooleanGlobalFilter | SelectionGlobalFilter;
}
