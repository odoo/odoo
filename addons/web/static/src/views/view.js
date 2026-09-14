// @ts-check
/** @odoo-module native */

import {
    Component,
    markRaw,
    onWillStart,
    onWillUpdateProps,
    reactive,
    toRaw,
    useSubEnv,
} from "@odoo/owl";
import { useDebugCategory } from "@web/core/debug/debug_context";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { viewLog } from "@web/core/utils/asset_log";
import { deepCopy, shallowEqual } from "@web/core/utils/collections/objects";
import { KeepLast } from "@web/core/utils/concurrency";
import { parseXML } from "@web/core/utils/dom/xml";
import { nbsp } from "@web/core/utils/format/strings";
import { useService } from "@web/core/utils/hooks";
import { extractLayoutComponents } from "@web/search/layout";
import { WithSearch } from "@web/search/with_search/with_search";
import { session } from "@web/session";
import { elementToIR, irToElement, literalNbsp } from "@web/views/ir/view_ir";
import { useActionLinks } from "@web/views/view_hook";

import {
    computeViewClassName,
    defaultViewProps,
    reportViewProps,
} from "./view_utils.js";

/**
 * @typedef {import("./view_config").ViewConfig} ViewConfig
 * @typedef {import("@web/core/context").Context} Context
 * @typedef {import("@web/env").OdooEnv} OdooEnv
 * @typedef {import("@web/core/utils/order_by").OrderTerm} OrderTerm
 * @typedef ViewProps
 * @property {string} resModel
 * @property {ViewType} type
 * @property {string} [arch]
 * @property {Record<string, any>} [fields]
 * @property {Record<string, any>} [relatedModels]
 * @property {number|false} [viewId]
 * @property {[number|false, string][]} [views]
 * @property {Record<string, any>} [actionMenus]
 * @property {boolean} [loadActionMenus=false]
 * @property {string} [searchViewArch]
 * @property {import("@web/views/ir/view_ir_schema").ViewIRNode} [searchViewIR]
 * @property {Record<string, any>} [searchViewFields]
 * @property {number|false} [searchViewId]
 * @property {Record<string, any>[]} [irFilters]
 * @property {boolean} [loadIrFilters=false]
 * @property {Context} [context={}]
 * @property {any} [domain]
 * @property {string[]} [groupBy]
 * @property {OrderTerm[]} [orderBy]
 * @property {boolean} [useSampleModel]
 * @property {string|import("@odoo/owl").Markup|false} [noContentHelp]
 * @property {string} [className]
 * @property {string} [jsClass]
 * @property {boolean} [noBreadcrumbs]
 * @property {Record<string, any>} [display={}]
 * @property {boolean} [activateFavorite]
 * @property {Record<string, any>[]} [dynamicFilters]
 * @property {boolean} [hideCustomGroupBy]
 * @property {string[]} [searchMenuTypes]
 * @property {Record<string, any>} [globalState]
 * @typedef {"activity"
 * | "calendar"
 * | "cohort"
 * | "form"
 * | "gantt"
 * | "graph"
 * | "grid"
 * | "hierarchy"
 * | "kanban"
 * | "list"
 * | "map"
 * | "pivot"
 * | "search"
 * } ViewType
 */

const viewRegistry = registry.category("views");

viewRegistry.addValidation({
    // a page without view_info (the login page, a frontend bundle) still
    // registers views; a validator that throws there drops the view instead
    type: {
        validate: (/** @type {any} */ t) =>
            typeof t === "string" && (!session.view_info || t in session.view_info),
    },

    Controller: {
        validate: (/** @type {any} */ c) => c.prototype instanceof Component,
    },
    Renderer: {
        validate: (/** @type {any} */ c) => c.prototype instanceof Component,
        optional: true,
    },
    ControlPanel: {
        validate: (/** @type {any} */ c) => c.prototype instanceof Component,
        optional: true,
    },
    SearchPanel: {
        validate: (/** @type {any} */ c) => c.prototype instanceof Component,
        optional: true,
    },
    Model: { type: Function, optional: true },
    SearchModel: { type: Function, optional: true },
    ArchParser: { type: Function, optional: true },
    Compiler: { type: Function, optional: true },

    props: { type: Function, optional: true },
    modelParams: {
        validate: (/** @type {any} */ m) =>
            typeof m?.fromState === "function" && typeof m?.fromArch === "function",
        optional: true,
    },
    buttonTemplate: { type: String, optional: true },
    display: { type: Object, optional: true },
    searchMenuTypes: { type: Array, element: String, optional: true },
    canOrderByCount: { type: Boolean, optional: true },
    hideCustomGroupBy: { type: Boolean, optional: true },
});

/**
 * The controller's props from the descriptor's declaration: a `props` factory
 * when it still has one, `modelParams` {fromState, fromArch} for a report-shaped
 * view, the parsed arch for everything with an ArchParser, and the generic
 * props alone for a descriptor declaring none of the three.
 *
 * @param {any} descr
 * @param {Record<string, any>} controllerProps
 * @param {any} config
 * @returns {Record<string, any>}
 */
export function buildComponentProps(descr, controllerProps, config) {
    if (descr.props) {
        return descr.props(controllerProps, descr, config);
    }
    if (descr.modelParams) {
        return reportViewProps(controllerProps, descr, descr.modelParams, config);
    }
    if (descr.ArchParser) {
        return defaultViewProps(controllerProps, descr);
    }
    return controllerProps;
}

export function getDefaultConfig() {
    const breadcrumbReactive = reactive([{ name: undefined }]);
    return {
        actionId: false,
        actionType: false,
        cache: true,
        actionXmlId: false,
        /** @type {any[]} */
        embeddedActions: [],
        currentEmbeddedActionId: false,
        parentActionId: false,
        breadcrumbs: breadcrumbReactive,
        disableSearchBarAutofocus: false,
        getDisplayName: () => breadcrumbReactive[0].name,
        historyBack: () => {},
        pagerProps: {},
        setDisplayName: (/** @type {any} */ newDisplayName) => {
            breadcrumbReactive[0].name = newDisplayName;
        },
        /** @type {any[]} */
        viewSwitcherEntries: [],
        /** @type {any[]} */
        views: [],
    };
}

const log = makeLogger("web.view");

export class ViewNotFoundError extends Error {}

const CALLBACK_RECORDER_NAMES = [
    "__beforeLeave__",
    "__getGlobalState__",
    "__getLocalState__",
    "__getContext__",
    "__getOrderBy__",
];

export const viewProps = {
    resModel: { type: String, optional: true },
    type: { type: String, optional: true },
    jsClass: { type: String, optional: true },

    arch: { type: String, optional: true },
    fields: { type: Object, optional: true },
    relatedModels: { type: Object, optional: true },
    viewId: { type: [Number, Boolean], optional: true },
    views: { type: Array, optional: true },
    actionMenus: { type: Object, optional: true },
    loadActionMenus: { type: Boolean, optional: true },

    searchViewArch: { type: String, optional: true },
    searchViewIR: { type: Object, optional: true },
    searchViewFields: { type: Object, optional: true },
    searchViewId: { type: [Number, Boolean], optional: true },
    irFilters: { type: Array, optional: true },
    loadIrFilters: { type: Boolean, optional: true },

    context: { type: Object, optional: true },
    domain: { type: Array, optional: true },
    groupBy: { type: Array, element: String, optional: true },
    orderBy: { type: Array, optional: true },

    useSampleModel: { type: Boolean, optional: true },
    noContentHelp: { type: [String, Boolean], optional: true },
    className: { type: String, optional: true },
    noBreadcrumbs: { type: Boolean, optional: true },

    display: { type: Object, optional: true },
    globalState: { type: Object, optional: true },

    activateFavorite: { type: Boolean, optional: true },
    dynamicFilters: { type: Array, optional: true },
    hideCustomGroupBy: { type: Boolean, optional: true },
    searchMenuTypes: { type: Array, element: String, optional: true },

    __beforeLeave__: { type: Object, optional: true },
    __getGlobalState__: { type: Object, optional: true },
    __getLocalState__: { type: Object, optional: true },
    __getContext__: { type: Object, optional: true },
    __getOrderBy__: { type: Object, optional: true },

    "*": true,
};

/** @type {string[]} */
const FORWARDED_TO_CONTROLLER = ["noBreadcrumbs"];

/**
 * @param {Record<string, any>} props
 * @param {Record<string, any>} declared
 * @returns {Record<string, any>}
 */
function pickDeclaredProps(props, declared) {
    /** @type {Record<string, any>} */
    const picked = {};
    for (const key of Object.keys(props)) {
        if (key in declared) {
            picked[key] = props[key];
        }
    }
    return picked;
}

export const STANDARD_PROPS = Object.keys(viewProps).filter(
    (key) => key !== "*" && !FORWARDED_TO_CONTROLLER.includes(key),
);

const ACTIONS = [
    "create",
    "delete",
    "edit",
    "group_create",
    "group_delete",
    "group_edit",
];

/**
 * @typedef {{ views: [number | false, string][], viewId: number | false | undefined, searchViewId: number | false | undefined }} ViewSelection
 * @typedef {{
 * viewDescription: any,
 * arch: string | undefined,
 * ir: import("@web/views/ir/view_ir_schema").ViewIRNode | undefined,
 * fields: Record<string, any> | undefined,
 * relatedModels: Record<string, any> | undefined,
 * actionMenus: Record<string, any> | undefined,
 * searchViewId: number | false | undefined,
 * searchViewArch: string | undefined,
 * searchViewIR: import("@web/views/ir/view_ir_schema").ViewIRNode | undefined,
 * searchViewFields: Record<string, any> | undefined,
 * irFilters: Record<string, any>[] | undefined,
 * }} LoadedView
 */

/**
 * @param {ViewProps} props
 * @param {any[]} configViews
 * @returns {ViewSelection}
 */
function resolveViewSelection(props, configViews) {
    const { type } = props;
    let { viewId, searchViewId } = props;
    const views = deepCopy(props.views || configViews);
    const view = views.find((/** @type {any} */ v) => v[1] === type) || [];
    if (view.length) {
        view[0] = viewId !== undefined ? viewId : view[0];
        viewId = view[0];
    } else {
        view.push(viewId || false, type);
        views.push(view);
    }
    const searchView = views.find((/** @type {any} */ v) => v[1] === "search");
    if (searchView) {
        searchView[0] = searchViewId !== undefined ? searchViewId : searchView[0];
        searchViewId = searchView[0];
    } else if (searchViewId !== undefined) {
        views.push([searchViewId, "search"]);
    }
    return { views, viewId, searchViewId };
}

/**
 * The element every parser and compiler walks. The server's IR is the
 * contract; the arch string is kept for a caller that hands one in through
 * props (embedded views, tests) and for a payload that predates the IR.
 *
 * @param {Pick<LoadedView, "arch" | "ir">} loaded
 * @param {Record<string, any>} context
 * @returns {{ archXmlDoc: Element, archIR: import("@web/views/ir/view_ir_schema").ViewIRNode }}
 */
function parseViewArch({ arch, ir }, context) {
    const source = ir ? "ir" : "arch";
    log.logic("archSource", { source });
    const archXmlDoc =
        source === "ir"
            ? irToElement(/** @type {NonNullable<typeof ir>} */ (ir), {
                  text: literalNbsp,
              })
            : parseXML((arch ?? "").replaceAll("&amp;nbsp;", nbsp));
    /** @type {Record<string, string>} */
    const disabled = {};
    for (const action of ACTIONS) {
        if (action in context && !context[action]) {
            archXmlDoc.setAttribute(action, "0");
            disabled[action] = "0";
        }
    }
    // the payload's IR is cached by the ORM service: never mutate it, clone the root
    const archIR = ir
        ? { ...ir, attrs: { ...ir.attrs, ...disabled } }
        : elementToIR(archXmlDoc);
    return { archXmlDoc, archIR };
}

/**
 * @param {ViewProps} props
 * @param {Element} archXmlDoc
 * @returns {boolean}
 */
function resolveUseSampleModel(props, archXmlDoc) {
    if ("useSampleModel" in props) {
        return /** @type {boolean} */ (props.useSampleModel);
    }
    const sample = archXmlDoc.getAttribute("sample");
    return sample ? evaluateBooleanExpr(sample) : false;
}

/**
 * @param {Record<string, any> | undefined} display
 * @param {Record<string, any>} viewDisplay
 * @returns {Record<string, any>}
 */
function mergeViewDisplay(display, viewDisplay) {
    const merged = { ...display };
    for (const [key, value] of Object.entries(deepCopy(viewDisplay))) {
        const current = merged[key];
        if (current && typeof current === "object") {
            merged[key] = { ...current, ...value };
        } else if (!(key in merged) || current) {
            merged[key] = value;
        }
    }
    return merged;
}

/** @extends {Component<ViewProps, import("@web/env").OdooEnv>} */
export class View extends Component {
    static template = "web.View";
    static components = { WithSearch };
    static searchMenuTypes = ["filter", "groupBy", "favorite"];
    static canOrderByCount = false;

    /** @type {number} */
    loadViewId;
    static defaultProps = {
        display: {},
        context: {},
        loadActionMenus: false,
        loadIrFilters: false,
        className: "",
    };
    static props = viewProps;

    /** @type {import("services").ServiceFactories["view"]} */
    viewService;
    /** @type {Record<string, any> | null} */
    withSearchProps;

    setup() {
        const {
            arch,
            fields,
            resModel,
            searchViewArch,
            searchViewIR,
            searchViewFields,
            type,
        } = this.props;
        if (!resModel) {
            throw Error(`View props should have a "resModel" key`);
        }
        if (!type) {
            throw Error(`View props should have a "type" key`);
        }
        if ((arch && !fields) || (!arch && fields)) {
            throw new Error(`"arch" and "fields" props must be given together`);
        }
        const searchView = searchViewArch || searchViewIR;
        if ((searchView && !searchViewFields) || (!searchView && searchViewFields)) {
            throw new Error(
                `"searchViewArch"/"searchViewIR" and "searchViewFields" props must be given together`,
            );
        }

        this.viewService = useService("view");
        this.withSearchProps = null;
        this.loadViewId = 0;

        useSubEnv({
            keepLast: new KeepLast(),
            config: {
                ...getDefaultConfig(),
                ...this.env.config,
            },
            ...Object.fromEntries(
                CALLBACK_RECORDER_NAMES.map((name) => [name, this.props[name] || null]),
            ),
        });

        this.handleActionLinks = useActionLinks({ resModel });

        useLifecycleLog(log);
        onWillStart(() => this.loadView(this.props));
        onWillUpdateProps((nextProps) => this.onWillUpdateProps(nextProps));

        useDebugCategory("view", { component: this });
    }

    /** @param {ViewProps} props */
    async loadView(props) {
        const loadId = ++this.loadViewId;
        const { resModel, type } = props;
        viewLog("load", type, resModel || "");
        const endLoad = log.perf(`loadView ${type} ${resModel || ""}`);
        log.pipeline("loadView", () => ({
            loadId,
            type,
            resModel,
            viewId: props.viewId,
        }));
        const config = /** @type {ViewConfig & Record<string, any>} */ (
            this.env.config
        );
        if (!session.view_info[type]) {
            throw new Error(`Invalid view type: ${type}`);
        }

        const selection = resolveViewSelection(props, config.views);
        const loaded = await this.loadViewDescriptions(props, selection, config);
        if (loadId !== this.loadViewId) {
            endLoad({ loadId, superseded: true });
            return;
        }
        config.views = selection.views;

        const { archXmlDoc, archIR } = parseViewArch(loaded, props.context ?? {});
        const jsClass = archXmlDoc.hasAttribute("js_class")
            ? /** @type {string} */ (archXmlDoc.getAttribute("js_class"))
            : props.jsClass || type;
        const descr = /** @type {any} */ (viewRegistry.get(jsClass));
        log.logic("resolve", () => ({
            loadId,
            jsClass,
            controller: descr.Controller?.name,
        }));

        Object.assign(config, {
            rawArch: loaded.arch,
            viewArch: archXmlDoc,
            viewIR: archIR,
            viewId: loaded.viewDescription.id,
            searchViewId: loaded.searchViewId,
            viewType: type,
            viewSubType: jsClass,
            noBreadcrumbs: props.noBreadcrumbs,
            ...extractLayoutComponents(descr),
        });

        const searchMenuTypes =
            props.searchMenuTypes ||
            descr.searchMenuTypes ||
            /** @type {any} */ (this.constructor).searchMenuTypes;
        const controllerProps = this.getControllerProps(props, loaded, archXmlDoc, {
            searchMenuTypes,
            archIR,
        });
        this.Controller = descr.Controller;
        this.componentProps = buildComponentProps(descr, controllerProps, config);
        this.withSearchProps = this.getWithSearchProps(props, loaded, archXmlDoc, {
            descr,
            searchMenuTypes,
        });
        endLoad({ loadId, jsClass });
    }

    /**
     * @param {ViewProps} props
     * @param {ViewSelection} selection
     * @param {ViewConfig & Record<string, any>} config
     * @returns {Promise<LoadedView>}
     */
    async loadViewDescriptions(props, selection, config) {
        const { views, viewId } = selection;
        const { resModel, type, loadActionMenus, loadIrFilters } = props;
        const context = /** @type {Record<string, any>} */ (props.context ?? {});
        let { searchViewId } = selection;
        let { arch, fields, relatedModels, searchViewArch, searchViewFields } = props;
        let { searchViewIR } = props;
        let { irFilters, actionMenus } = props;

        const hasSearchView = views.some((/** @type {any} */ v) => v[1] === "search");
        const mustLoadView = !arch || (!actionMenus && loadActionMenus);
        const mustLoadSearchView =
            hasSearchView &&
            ((searchViewId !== undefined && !searchViewArch && !searchViewIR) ||
                (!irFilters && loadIrFilters));

        /** @type {any} */
        let viewDescription = { id: viewId, resModel, type };
        if (mustLoadView || mustLoadSearchView) {
            const options = {
                actionId: config.actionId,
                loadActionMenus,
                loadIrFilters: loadIrFilters && hasSearchView,
            };
            if (config.currentEmbeddedActionId) {
                options.embeddedActionId = config.currentEmbeddedActionId;
                options.embeddedParentResId = context.active_id;
            }
            viewLog("loadViews", resModel, type);
            const result = await this.viewService.loadViews(
                { context, resModel, views },
                options,
            );
            viewDescription = result.views[type];
            const searchViewDescription = /** @type {any} */ (result.views).search;
            if (mustLoadSearchView) {
                searchViewId = searchViewId || searchViewDescription.id;
                if (!searchViewArch && !searchViewIR) {
                    searchViewArch = searchViewDescription.arch;
                    searchViewIR = searchViewDescription.ir;
                    searchViewFields = result.fields;
                }
                if (!irFilters) {
                    irFilters = searchViewDescription.irFilters;
                }
            }
            fields = fields || markRaw(result.fields);
            relatedModels = relatedModels || markRaw(result.relatedModels);
        }

        return {
            viewDescription,
            arch: arch || viewDescription.arch,
            ir: arch ? undefined : viewDescription.ir,
            fields,
            relatedModels,
            actionMenus: actionMenus || viewDescription.actionMenus,
            searchViewId,
            searchViewArch,
            searchViewIR,
            searchViewFields,
            irFilters,
        };
    }

    /**
     * @param {ViewProps} props
     * @param {LoadedView} loaded
     * @param {Element} archXmlDoc
     * @param {{ searchMenuTypes: string[], archIR: import("@web/views/ir/view_ir_schema").ViewIRNode }} params
     * @returns {Record<string, any>}
     */
    getControllerProps(props, loaded, archXmlDoc, { searchMenuTypes, archIR }) {
        const { resModel } = props;
        const { viewDescription, fields, relatedModels } = loaded;
        const info = {
            actionMenus: loaded.actionMenus,
            mode: props.display?.mode,
            irFilters: loaded.irFilters,
            searchViewArch: loaded.searchViewArch,
            searchViewIR: loaded.searchViewIR,
            searchViewFields: loaded.searchViewFields,
            searchViewId: loaded.searchViewId,
        };
        if (viewDescription.custom_view_id) {
            info.customViewId = viewDescription.custom_view_id;
        }
        if (props.noContentHelp) {
            info.noContentHelp = props.noContentHelp;
        }

        /** @type {Record<string, any>} */
        const controllerProps = {
            info,
            arch: archXmlDoc,
            ir: archIR,
            fields,
            relatedModels,
            resModel,
            useSampleModel: resolveUseSampleModel(props, archXmlDoc),
            className: computeViewClassName(props.type, archXmlDoc, [
                "o_view_controller",
                ...(props.className || "").split(" "),
            ]),
            searchMenuTypes,
        };
        if (props.globalState) {
            controllerProps.globalState = props.globalState;
        }
        for (const key of Object.keys(props)) {
            if (!STANDARD_PROPS.includes(key)) {
                controllerProps[key] = props[key];
            }
        }
        return controllerProps;
    }

    /**
     * @param {ViewProps} props
     * @param {LoadedView} loaded
     * @param {Element} archXmlDoc
     * @param {{ descr: Record<string, any>, searchMenuTypes: string[] }} params
     * @returns {Record<string, any>}
     */
    getWithSearchProps(props, loaded, archXmlDoc, { descr, searchMenuTypes }) {
        /** @type {Record<string, any>} */
        const withSearchProps = {
            ...pickDeclaredProps(toRaw(props), WithSearch.props),
            hideCustomGroupBy: props.hideCustomGroupBy || descr.hideCustomGroupBy,
            searchMenuTypes,
            canOrderByCount:
                descr.canOrderByCount ||
                /** @type {any} */ (this.constructor).canOrderByCount,
            SearchModel: descr.SearchModel,
        };
        if (loaded.searchViewId !== undefined) {
            withSearchProps.searchViewId = loaded.searchViewId;
        }
        if (loaded.searchViewArch || loaded.searchViewIR) {
            withSearchProps.searchViewArch = loaded.searchViewArch;
            withSearchProps.searchViewIR = loaded.searchViewIR;
            withSearchProps.searchViewFields = loaded.searchViewFields;
        }
        if (loaded.irFilters) {
            withSearchProps.irFilters = loaded.irFilters;
        }
        if (descr.display) {
            withSearchProps.display = mergeViewDisplay(
                withSearchProps.display,
                descr.display,
            );
        }
        const defaultGroupBy = archXmlDoc.getAttribute("default_group_by");
        if (defaultGroupBy) {
            withSearchProps.defaultGroupBy = defaultGroupBy.split(",");
        }
        return withSearchProps;
    }

    /** @type {string[]} */
    static VIEW_SELECTING_PROPS = ["arch", "type", "resModel", "viewId", "jsClass"];

    /** @param {ViewProps} nextProps */
    onWillUpdateProps(nextProps) {
        const selectors = /** @type {typeof View} */ (this.constructor)
            .VIEW_SELECTING_PROPS;
        const reselected = selectors.some((key) => this.props[key] !== nextProps[key]);
        const viewsChanged = !shallowEqual(
            this.props.views ?? [],
            nextProps.views ?? [],
            shallowEqual,
        );
        log.logic("onWillUpdateProps", () => ({
            reselected,
            viewsChanged,
            type: nextProps.type,
        }));
        if (reselected || viewsChanged) {
            return this.loadView(nextProps);
        }
        const { context, domain, groupBy, orderBy } = nextProps;
        Object.assign(/** @type {Record<string, any>} */ (this.withSearchProps), {
            context,
            domain,
            groupBy,
            orderBy,
        });
    }
}
