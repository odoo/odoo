/**
 * Type declarations for the views module (`@web/views/`).
 *
 * Covers the View component, view service, view utilities, arch parsers,
 * controllers, renderers, and shared view infrastructure.
 */

// ---------------------------------------------------------------------------
// View service
// ---------------------------------------------------------------------------

declare module "@web/views/view_service" {
    export interface IrFilter {
        user_id: [number, string] | false;
        sort: string;
        context: string;
        name: string;
        domain: string;
        id: number;
        is_default: boolean;
        model_id: string;
        action_id: [number, string] | false;
        embedded_action_id: number | false;
        embedded_parent_res_id: number | false;
    }

    export interface ViewDescription {
        arch: string;
        id: number | false;
        custom_view_id?: number | null;
        actionMenus?: Record<string, any[]>;
        irFilters?: IrFilter[];
    }

    export interface LoadViewsParams {
        resModel: string;
        views: [number | false, string][];
        context: Record<string, any>;
    }

    export interface LoadViewsOptions {
        actionId?: number | false;
        embeddedActionId?: number | false;
        embeddedParentResId?: number | false;
        loadActionMenus?: boolean;
        loadIrFilters?: boolean;
        [key: string]: any;
    }

    export type ViewDescriptions = Record<string, ViewDescription> & {
        fields: Record<string, any>;
        relatedModels: Record<string, any>;
        views: Record<string, ViewDescription>;
    };

    export interface ViewService {
        loadViews(
            params: LoadViewsParams,
            options?: LoadViewsOptions,
        ): Promise<ViewDescriptions>;
    }

    export const viewService: {
        dependencies: string[];
        async: string[];
        start(
            env: any,
            services: Record<string, any>,
        ): ViewService;
    };
}

// ---------------------------------------------------------------------------
// View component
// ---------------------------------------------------------------------------

declare module "@web/views/view" {
    import { Component } from "@odoo/owl";

    export type ViewType =
        | "activity"
        | "calendar"
        | "cohort"
        | "form"
        | "gantt"
        | "graph"
        | "grid"
        | "hierarchy"
        | "kanban"
        | "list"
        | "map"
        | "pivot"
        | "search";

    export interface ViewProps {
        resModel: string;
        type: ViewType;
        arch?: string;
        fields?: Record<string, any>;
        relatedModels?: Record<string, any>;
        viewId?: number | false;
        views?: [number | false, string][];
        actionMenus?: Record<string, any[]>;
        loadActionMenus?: boolean;
        searchViewArch?: string;
        searchViewFields?: Record<string, any>;
        searchViewId?: number | false;
        irFilters?: any[];
        loadIrFilters?: boolean;
        context?: Record<string, any>;
        domain?: any[];
        groupBy?: string[];
        orderBy?: Array<{ name: string; asc?: boolean }>;
        useSampleModel?: boolean;
        noContentHelp?: string;
        className?: string;
        jsClass?: string;
        noBreadcrumbs?: boolean;
        display?: Record<string, any>;
        globalState?: Record<string, any>;
        [key: string]: any;
    }

    export interface ViewRegistryEntry {
        type: ViewType;
        Controller: typeof Component;
        Renderer?: typeof Component;
        ArchParser?: new () => { parse(...args: any[]): any };
        Model?: any;
        Compiler?: any;
        SearchModel?: any;
        searchMenuTypes?: string[];
        canOrderByCount?: boolean;
        buttonTemplate?: string;
        display?: Record<string, any>;
        hideCustomGroupBy?: boolean;
        props?: (
            genericProps: Record<string, any>,
            view: ViewRegistryEntry,
            config?: Record<string, any>,
        ) => Record<string, any>;
    }

    export function getDefaultConfig(): Record<string, any>;

    export class ViewNotFoundError extends Error {}

    export class View extends Component {
        static searchMenuTypes: string[];
        static canOrderByCount: boolean;
    }
}

// ---------------------------------------------------------------------------
// View utilities
// ---------------------------------------------------------------------------

declare module "@web/views/view_utils" {
    export interface ViewActiveActions {
        type: "view";
        edit: boolean;
        create: boolean;
        delete: boolean;
        duplicate: boolean;
    }

    export function computeViewClassName(
        viewType: string | null,
        rootNode: Element | null,
        additionalClassList?: string[],
    ): string;

    export function getFormattedValue(
        record: any,
        fieldName: string,
        fieldInfo?: any,
    ): string;

    export function getActiveActions(rootNode: Element): ViewActiveActions;

    export function isX2Many(field: any): boolean;
    export function isNumeric(field: any): boolean;
    export function isNull(value: any): boolean;
    export function toStringExpression(str: string): string;

    export function computeModelOptions(
        env: any,
        display: Record<string, any>,
    ): { lazy: boolean };

    export function useControllerServices(): {
        action: any;
        dialog: any;
        notification: any;
        orm: any;
        uiHooks: Record<string, Function>;
    };

    export function computeArchiveEnabled(
        fields: Record<string, any>,
    ): boolean;

    export function buildActionMenuItems(
        staticItems: Record<string, any>,
        actionMenus?: { action?: any[]; print?: any[] },
    ): { action: any[]; print: any[] };

    export function makeModelUIHooks(services: {
        action: any;
        dialog: any;
        notification: any;
    }): Record<string, Function>;
}

// ---------------------------------------------------------------------------
// View hooks
// ---------------------------------------------------------------------------

declare module "@web/views/view_hook" {
    export function useActionLinks(params: {
        resModel: string;
        reload?: () => void;
    }): (ev: Event) => void;

    export function useBounceButton(
        containerRef: { el: HTMLElement | null },
        shouldBounce: (target: HTMLElement) => boolean,
    ): void;

    export function useExportRecords(
        env: any,
        context: Record<string, any>,
        getDefaultExportList: () => any[],
    ): () => void;

    export function useDeleteRecords(
        model: any,
    ): (dialogProps?: Record<string, any>, records?: any[]) => void;
}

// ---------------------------------------------------------------------------
// View buttons
// ---------------------------------------------------------------------------

declare module "@web/views/view_buttons" {
    export const BUTTON_CLICK_PARAMS: string[];

    export function processButton(node: Element): {
        className: string;
        disabled: boolean;
        icon: string | false;
        title: string | undefined;
        string: string | undefined;
        options: Record<string, any>;
        display: string;
        clickParams: Record<string, any>;
        column_invisible: string | null;
        invisible: string | null;
        readonly: string | null;
        required: string | null;
        attrs: Record<string, string>;
    };
}

declare module "@web/views/view_button/view_button" {
    import { Component } from "@odoo/owl";
    export class ViewButton extends Component {}
}

declare module "@web/views/view_button/view_button_hook" {
    export function useViewButtons(
        rootRef: { el: HTMLElement | null },
        callbacks: {
            beforeExecuteAction?: (clickParams: any) => Promise<any>;
            afterExecuteAction?: (clickParams: any) => Promise<any>;
            reload?: () => Promise<void> | void;
        },
    ): void;

    export function executeButtonCallback(
        activeElement: HTMLElement,
        callback: () => Promise<any>,
    ): Promise<any>;
}

// ---------------------------------------------------------------------------
// View measurements
// ---------------------------------------------------------------------------

declare module "@web/views/view_measurements" {
    export function computeReportMeasures(
        fields: Record<string, any>,
        fieldAttrs: Record<string, any>,
        activeMeasures: string[],
        options?: { sumAggregatorOnly?: boolean },
    ): Record<string, any>;

    export function computeAggregatedValue(
        values: number[],
        aggregator: "sum" | "avg" | "min" | "max" | "count" | "count_distinct",
    ): number;

    export function processMeasure(measure: any): any;
}

// ---------------------------------------------------------------------------
// Standard view props
// ---------------------------------------------------------------------------

declare module "@web/views/standard_view_props" {
    export const standardViewProps: Record<string, any>;
}

// ---------------------------------------------------------------------------
// Multi-record controller
// ---------------------------------------------------------------------------

declare module "@web/views/multi_record_controller" {
    import { Component } from "@odoo/owl";

    export class MultiRecordController extends Component {
        model: any;
        archInfo: any;
        rootRef: { el: HTMLElement | null };
        archiveEnabled: boolean;
        firstLoad: boolean;

        initMultiRecordBehavior(): void;

        get actionMenuItems(): { action: any[]; print: any[] };
        get actionMenuProps(): Record<string, any>;
        get display(): Record<string, any>;
        get hasSelectedRecords(): boolean;
        get isDomainSelected(): boolean;
        get modelOptions(): { lazy: boolean };

        getStaticActionMenuItems(): Record<string, any>;
        getExportableFields(): any[];
        onSelectionChanged(): Promise<void>;
        onPageChangeScroll(): void;
        onDeleteSelectedRecords(): void;
        beforeExecuteActionButton(clickParams: any): Promise<any>;
        afterExecuteActionButton(clickParams: any): Promise<any>;
    }
}

// ---------------------------------------------------------------------------
// Form view
// ---------------------------------------------------------------------------

declare module "@web/views/form/form_controller" {
    import { Component } from "@odoo/owl";

    export class FormController extends Component {
        model: any;
        archInfo: any;
        rootRef: { el: HTMLElement | null };

        displayName(): string;
        save(params?: Record<string, any>): Promise<boolean>;
        create(): Promise<void>;
        discard(): Promise<void>;
        duplicateRecord(): Promise<void>;
        deleteRecord(): Promise<void>;
        beforeExecuteActionButton(clickParams: any): Promise<any>;
        afterExecuteActionButton(clickParams: any): Promise<any>;
    }
}

declare module "@web/views/form/form_renderer" {
    import { Component } from "@odoo/owl";
    export class FormRenderer extends Component {}
}

declare module "@web/views/form/form_arch_parser" {
    export class FormArchParser {
        parse(
            xmlDoc: Element,
            models: Record<string, any>,
            modelName: string,
        ): {
            activeActions: Record<string, boolean>;
            autofocusFieldIds: string[];
            disableAutofocus: boolean;
            fieldNodes: Record<string, any>;
            widgetNodes: Record<string, any>;
            xmlDoc: Element;
        };
    }
}

declare module "@web/views/form/form_compiler" {
    export class FormCompiler {
        setup(): void;
        compile(node: Element, params?: Record<string, any>): Element;
    }
}

declare module "@web/views/form/form_utils" {
    export function loadSubViews(
        fieldNodes: Record<string, any>,
        fields: Record<string, any>,
        context: Record<string, any>,
        resModel: string,
        viewService: any,
        isSmall: boolean,
    ): Promise<void>;

    export function useFormViewInDialog(): void;
}

// ---------------------------------------------------------------------------
// List view
// ---------------------------------------------------------------------------

declare module "@web/views/list/list_controller" {
    import { MultiRecordController } from "@web/views/multi_record_controller";
    export class ListController extends MultiRecordController {}
}

declare module "@web/views/list/list_renderer" {
    import { Component } from "@odoo/owl";
    export class ListRenderer extends Component {}
}

declare module "@web/views/list/list_arch_parser" {
    export class ListArchParser {
        parse(xmlDoc: Element, models: Record<string, any>, modelName: string): Record<string, any>;
    }
}

// ---------------------------------------------------------------------------
// Kanban view
// ---------------------------------------------------------------------------

declare module "@web/views/kanban/kanban_controller" {
    import { MultiRecordController } from "@web/views/multi_record_controller";
    export class KanbanController extends MultiRecordController {}
}

declare module "@web/views/kanban/kanban_renderer" {
    import { Component } from "@odoo/owl";
    export class KanbanRenderer extends Component {}
}

declare module "@web/views/kanban/kanban_record" {
    import { Component } from "@odoo/owl";
    export class KanbanRecord extends Component {}
}

declare module "@web/views/kanban/kanban_arch_parser" {
    export class KanbanArchParser {
        parse(xmlDoc: Element, models: Record<string, any>, modelName: string): Record<string, any>;
    }
}

// ---------------------------------------------------------------------------
// Calendar view
// ---------------------------------------------------------------------------

declare module "@web/views/calendar/calendar_controller" {
    import { Component } from "@odoo/owl";
    export class CalendarController extends Component {}
}

declare module "@web/views/calendar/calendar_model" {
    export class CalendarModel {
        load(params: Record<string, any>): Promise<void>;
        get data(): Record<string, any>;
        get records(): any[];
        get date(): any;
        get scale(): string;
        get rangeStart(): any;
        get rangeEnd(): any;
    }
}

declare module "@web/views/calendar/calendar_arch_parser" {
    export class CalendarArchParser {
        parse(xmlDoc: Element, models: Record<string, any>, modelName: string): Record<string, any>;
    }
}

// ---------------------------------------------------------------------------
// Graph view
// ---------------------------------------------------------------------------

declare module "@web/views/graph/graph_controller" {
    import { Component } from "@odoo/owl";
    export class GraphController extends Component {}
}

declare module "@web/views/graph/graph_model" {
    export class GraphModel {
        load(searchParams: Record<string, any>): Promise<void>;
        get data(): Record<string, any>;
    }
}

declare module "@web/views/graph/graph_renderer" {
    import { Component } from "@odoo/owl";
    export class GraphRenderer extends Component {}
}

// ---------------------------------------------------------------------------
// Pivot view
// ---------------------------------------------------------------------------

declare module "@web/views/pivot/pivot_controller" {
    import { Component } from "@odoo/owl";
    export class PivotController extends Component {}
}

declare module "@web/views/pivot/pivot_model" {
    export class PivotModel {
        load(searchParams: Record<string, any>): Promise<void>;
        get data(): Record<string, any>;
    }
}

declare module "@web/views/pivot/pivot_renderer" {
    import { Component } from "@odoo/owl";
    export class PivotRenderer extends Component {}
}

// ---------------------------------------------------------------------------
// View dialogs
// ---------------------------------------------------------------------------

declare module "@web/views/view_dialogs/form_view_dialog" {
    import { Component } from "@odoo/owl";
    export class FormViewDialog extends Component {}
}

declare module "@web/views/view_dialogs/select_create_dialog" {
    import { Component } from "@odoo/owl";
    export class SelectCreateDialog extends Component {}
}

declare module "@web/views/view_dialogs/export_data_dialog" {
    import { Component } from "@odoo/owl";
    export class ExportDataDialog extends Component {}
}

// ---------------------------------------------------------------------------
// Widgets
// ---------------------------------------------------------------------------

declare module "@web/views/widgets/widget" {
    import { Component } from "@odoo/owl";
    export class Widget extends Component {
        static parseWidgetNode(node: Element): Record<string, any>;
    }
}

declare module "@web/views/widgets/standard_widget_props" {
    export const standardWidgetProps: Record<string, any>;
}

// ---------------------------------------------------------------------------
// View compiler
// ---------------------------------------------------------------------------

declare module "@web/views/view_compiler" {
    import { Component } from "@odoo/owl";

    export function toInterpolatedStringExpression(str: string): string;
    export function appendAttr(el: Element, attr: string, value: string): void;
    export function copyAttributes(el: Element, compiled: Element): void;
    export function encodeObjectForTemplate(obj: Record<string, any>): string;
    export function getModifier(el: Element, modifierName: string): string | null;
    export function isComponentNode(el: Element): boolean;
    export function isTextNode(node: Node): boolean;
    export function makeSeparator(title: string): Element;
    export function resetViewCompilerCache(): void;

    export function useViewCompiler(
        Compiler: any,
        templates: Record<string, Element>,
        options?: Record<string, any>,
    ): Record<string, any>;

    export class ViewCompiler {
        setup(): void;
        compilers: Record<string, (node: Element, params?: any) => Element>;
        compile(
            node: Element,
            params?: Record<string, any>,
        ): Element;
        compileNode(
            node: Element,
            params?: Record<string, any>,
            dynamic?: boolean,
        ): Element;
        compileGenericNode(
            node: Element,
            params?: Record<string, any>,
            dynamic?: boolean,
        ): Element;
        compileButton(
            node: Element,
            params?: Record<string, any>,
        ): Element;
        compileField(
            node: Element,
            params?: Record<string, any>,
        ): Element;
        [key: string]: any;
    }
}

// ---------------------------------------------------------------------------
// Action helper
// ---------------------------------------------------------------------------

declare module "@web/views/action_helper" {
    import { Component } from "@odoo/owl";
    export class ActionHelper extends Component {}
}
