// @ts-check
/** @odoo-module native */

/** @type {string[]} */
export const VIEW_CONFIG_SURFACE = [
    "actionId",
    "actionName",
    "actionType",
    "actionXmlId",
    "cache",
    "breadcrumbs",
    "getDisplayName",
    "setDisplayName",
    "historyBack",
    "noBreadcrumbs",
    "embeddedActions",
    "currentEmbeddedActionId",
    "parentActionId",
    "rawArch",
    "viewArch",
    "viewIR",
    "viewId",
    "searchViewId",
    "viewType",
    "viewSubType",
    "views",
    "viewSwitcherEntries",
    "ControlPanel",
    "SearchPanel",
    "disableSearchBarAutofocus",
    "pagerProps",
    "isReloadingController",
];

/** @type {string[]} */
export const VIEW_CONFIG_FOREIGN_SURFACE = ["limit", "offset", "onNodeClicked"];

/**
 * @typedef {{
 * actionId: number | false,
 * actionName?: string,
 * actionType: string | false,
 * actionXmlId?: string | false,
 * cache?: boolean,
 * breadcrumbs: { name?: string, [key: string]: any }[],
 * getDisplayName: () => string,
 * setDisplayName: (displayName: string) => void,
 * historyBack: () => void,
 * noBreadcrumbs?: boolean,
 * embeddedActions: any[],
 * currentEmbeddedActionId: number | false,
 * parentActionId: number | false,
 * rawArch?: string,
 * viewArch?: Element,
 * viewIR?: import("@web/views/ir/view_ir_schema").ViewIRNode,
 * viewId?: number | false,
 * searchViewId?: number | false,
 * viewType?: string,
 * viewSubType?: string,
 * views: any[],
 * viewSwitcherEntries: { type: string, [key: string]: any }[],
 * ControlPanel?: any,
 * SearchPanel?: any,
 * disableSearchBarAutofocus: boolean,
 * pagerProps: Record<string, any>,
 * isReloadingController?: boolean,
 * }} ViewConfig
 */
