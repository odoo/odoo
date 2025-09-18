/**
 * Type declarations for the search module (`@web/search/`).
 *
 * Provides ambient types for SearchModel (the central search state manager),
 * SearchArchParser, and the main component classes used across all views.
 */

declare module "@web/search/search_model" {
    import { EventBus } from "@odoo/owl";
    import { Domain } from "@web/core/domain";

    export type OrderTerm = { name: string; asc?: boolean };

    export interface Section {
        id: number;
        type: "category" | "filter";
        values: Map<any, Record<string, any>>;
        groups?: Map<any, Record<string, any>>;
        errorMsg?: string;
        fieldName?: string;
        description?: string;
        enableCounters?: boolean;
        limit?: number;
        icon?: string;
        color?: string;
        expand?: boolean;
        hierarchize?: string | false;
        activeValueId?: any;
        domain?: string;
        groupBy?: string | false;
        empty?: boolean;
    }

    export interface SearchItem {
        id: number;
        type: string;
        description: string;
        fieldName?: string;
        fieldType?: string;
        groupId?: number;
        groupNumber?: number;
        name?: string;
        isDefault?: boolean;
        isActive?: boolean;
        invisible?: string;
        context?: string;
        domain?: string;
        [key: string]: any;
    }

    export interface Field {
        name: string;
        type: string;
        string?: string;
        selection?: [string | number, string][];
        relation?: string;
        searchable?: boolean;
        sortable?: boolean;
        store?: boolean;
        groupable?: boolean;
        [key: string]: any;
    }

    export interface SearchParams {
        context: Record<string, any>;
        domain: any[];
        groupBy: string[];
        orderBy: OrderTerm[];
        resModel: string;
        resId?: number | false;
        resIds?: number[];
        useSampleModel?: boolean;
        [key: string]: any;
    }

    export class SearchModel extends EventBus {
        resModel: string;
        searchViewFields: Record<string, Field>;
        searchViewArch: string;
        searchItems: Record<number, SearchItem>;
        globalContext: Record<string, any>;
        globalDomain: any[];
        globalGroupBy: string[];
        globalOrderBy: OrderTerm[];
        hideCustomGroupBy: boolean;
        canOrderByCount: boolean;
        defaultGroupBy?: string[];
        query: any[];
        nextId: number;
        nextGroupId: number;
        display: Record<string, any>;
        orderByCount: string | false;
        sectionsPromise: Promise<void>;

        constructor(env: any, services: Record<string, any>, args?: any);
        load(config: Record<string, any>): Promise<void>;
        reload(config?: Record<string, any>): Promise<void>;

        // Getters — computed search state
        get categories(): Section[];
        get context(): Record<string, any>;
        get domain(): Domain;
        get domainString(): string;
        get facets(): any[];
        get filters(): Section[];
        get groupBy(): string[];
        get orderBy(): OrderTerm[];

        // Search item operations
        addAutoCompletionValues(searchItemId: number, autocompleteValue: any): void;
        clearQuery(): void;
        clearFilters(): void;
        createNewFavorite(params: {
            description: string;
            isDefault: boolean;
            isShared: boolean;
            embeddedActionId?: number | false;
        }): Promise<number>;
        createNewFilters(prefilters: any[]): void;
        createNewGroupBy(fieldName: string, options?: { interval?: string; invisible?: string }): void;
        deactivateGroup(groupId: number): void;
        exportState(): Record<string, any>;
        getSearchItems(predicate: (item: SearchItem) => boolean): SearchItem[];
        getSections(predicate?: (section: Section) => boolean): Section[];
        search(): void;
        splitAndAddDomain(domain: string, groupId?: number): Promise<void>;
        toggleCategoryValue(sectionId: number, valueId: any): void;
        toggleFilterValues(sectionId: number, valueIds: any[], forceTo?: boolean | null): void;
        clearSections(sectionIds: number[]): void;
        toggleSearchItem(searchItemId: number): void;
        toggleDateFilter(searchItemId: number, generatorId: string): void;
        toggleDateGroupBy(searchItemId: number, intervalId: string): void;
        spawnCustomFilterDialog(): Promise<void>;
        switchGroupBySort(): void;
        getSearchItemsProperties(searchItem: SearchItem): Promise<SearchItem[]>;
        fillSearchViewItemsProperty(): Promise<void>;
    }
}

declare module "@web/search/search_arch_parser" {
    export class SearchArchParser {
        constructor(
            searchViewDescription: { irFilters?: any[]; arch?: string },
            fields: Record<string, any>,
            searchDefaults?: Record<string, any>,
            searchPanelDefaults?: Record<string, any>,
        );
        parse(): {
            labels: Function[];
            preSearchItems: any[][];
            searchPanelInfo: { className: string; viewTypes: string[] };
            sections: any[][];
        };
    }
}

declare module "@web/search/with_search/with_search" {
    import { Component } from "@odoo/owl";
    export const SEARCH_KEYS: string[];
    export class WithSearch extends Component {}
}

declare module "@web/search/layout" {
    import { Component } from "@odoo/owl";
    export function extractLayoutComponents(params: Record<string, any>): Record<string, any>;
    export class Layout extends Component {}
}

declare module "@web/search/action_hook" {
    export const scrollSymbol: unique symbol;

    export class CallbackRecorder {
        get callbacks(): Function[];
        add(owner: any, callback: Function): void;
        remove(owner: any): void;
    }

    export function useCallbackRecorder(callbackRecorder: CallbackRecorder, callback: Function): void;
    export function useSetupAction(params?: {
        beforeVisibilityChange?: Function;
        beforeUnload?: Function;
        beforeLeave?: Function;
        getGlobalState?: () => Record<string, any>;
        getLocalState?: () => Record<string, any>;
        rootRef?: { el: HTMLElement | null };
        getContext?: () => Record<string, any>;
        getOrderBy?: () => any[];
    }): { setScrollFromState: Function };
}

declare module "@web/search/control_panel/control_panel" {
    import { Component } from "@odoo/owl";
    export class ControlPanel extends Component {}
}

declare module "@web/search/search_panel/search_panel" {
    import { Component } from "@odoo/owl";
    export class SearchPanel extends Component {}
}

declare module "@web/search/search_bar/search_bar" {
    import { Component } from "@odoo/owl";
    export class SearchBar extends Component {}
}

declare module "@web/search/breadcrumbs/breadcrumbs" {
    import { Component } from "@odoo/owl";
    export class Breadcrumbs extends Component {}
}

declare module "@web/search/utils/dates" {
    export const DEFAULT_INTERVAL: string;
    export const INTERVAL_OPTIONS: Record<string, { description: any; id: string; groupNumber: number }>;
    export const BACKEND_INTERVAL_OPTIONS: Record<string, { description: any; id: string; groupNumber?: number }>;

    export function constructDateDomain(referenceMoment: any, searchItem: any, selectedOptionIds: string[]): { domain: any; description: string };
    export function constructDateRange(params: any): { domain: any; description: string };
    export function getIntervalOptions(): any[];
    export function getOptionsWithDescriptions(options: Record<string, any>): any[];
    export function getPeriodOptions(referenceMoment: any, optionsParams: any): any[];
    export function toGeneratorId(unit: string, offset?: number): string;
    export function getSelectedOptions(referenceMoment: any, searchItem: any, selectedOptionIds: string[]): Record<string, any[]>;
    export function getSetParam(periodOption: any, referenceMoment: any): Record<string, any>;
    export function rankInterval(intervalOptionId: string): number;
    export function sortPeriodOptions(options: any[]): void;
    export function yearSelected(selectedOptionIds: string[]): boolean;
}

declare module "@web/search/utils/misc" {
    export const FACET_ICONS: Record<string, string>;
    export const FACET_COLORS: Record<string, number>;
    export const GROUPABLE_TYPES: string[];
}

declare module "@web/search/search_state" {
    export const SPECIAL: unique symbol;
    export const FAVORITE_PRIVATE_GROUP: number;
    export const FAVORITE_SHARED_GROUP: number;
    export function hasValues(section: any): boolean;
    export function mapToArray(map: Map<any, any>): any[][];
    export function arrayToMap(array: [any, any][]): Map<any, any>;
    export function execute(op: Function, source: any, target: any): void;
    export function extractSearchDefaults(globalContext: Record<string, any>): {
        searchDefaults: Record<string, any>;
        searchPanelDefaults: Record<string, any>;
    };
}
