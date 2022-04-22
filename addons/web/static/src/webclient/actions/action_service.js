/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { makeContext } from "@web/core/context";
import { useDebugCategory } from "@web/core/debug/debug_context";
import { download } from "@web/core/network/download";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { KeepLast } from "@web/core/utils/concurrency";
import { useBus, useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { cleanDomFromBootstrap } from "@web/legacy/utils";
import { View } from "@web/views/view";
import { ActionDialog } from "./action_dialog";
import { CallbackRecorder } from "./action_hook";

const { Component, hooks, tags } = owl;
const { useRef, useSubEnv } = hooks;

const actionHandlersRegistry = registry.category("action_handlers");
const actionRegistry = registry.category("actions");
const viewRegistry = registry.category("views");

/** @typedef {number|false} ActionId */
/** @typedef {Object} ActionDescription */
/** @typedef {"current" | "fullscreen" | "new" | "main" | "self" | "inline"} ActionMode */
/** @typedef {string} ActionTag */
/** @typedef {string} ActionXMLId */
/** @typedef {Object} Context */
/** @typedef {Function} CallableFunction */
/** @typedef {string} ViewType */

/** @typedef {ActionId|ActionXMLId|ActionTag|ActionDescription} ActionRequest */

/**
 * @typedef {Object} ActionOptions
 * @property {Context} [additionalContext]
 * @property {boolean} [clearBreadcrumbs]
 * @property {CallableFunction} [onClose]
 * @property {Object} [props]
 * @property {ViewType} [viewType]
 */

export function clearUncommittedChanges(env) {
    const callbacks = [];
    env.bus.trigger("CLEAR-UNCOMMITTED-CHANGES", callbacks);
    return Promise.all(callbacks.map((fn) => fn()));
}

function parseActiveIds(ids) {
    const activeIds = [];
    if (typeof ids === "string") {
        activeIds.push(...ids.split(",").map(Number));
    } else if (typeof ids === "number") {
        activeIds.push(ids);
    }
    return activeIds;
}

// -----------------------------------------------------------------------------
// Errors
// -----------------------------------------------------------------------------
export class ViewNotFoundError extends Error {}

export class ControllerNotFoundError extends Error {}

export class InvalidButtonParamsError extends Error {}

// -----------------------------------------------------------------------------
// ActionManager (Service)
// -----------------------------------------------------------------------------

// regex that matches context keys not to forward from an action to another
const CTX_KEY_REGEX = /^(?:(?:default_|search_default_|show_).+|.+_view_ref|group_by|group_by_no_leaf|active_id|active_ids|orderedBy)$/;

// only register this template once for all dynamic classes ControllerComponent
const ControllerComponentTemplate = tags.xml`<t t-component="Component" t-props="props"
    t-ref="component"
    t-on-history-back="onHistoryBack"
    t-on-controller-title-updated.stop="onTitleUpdated"/>`;

function makeActionManager(env) {
    const keepLast = new KeepLast();
    let id = 0;
    let controllerStack = [];
    let dialogCloseProm;
    let actionCache = {};
    let dialog = null;

    // The state action (or default user action if none) is loaded as soon as possible
    // so that the next "doAction" will have its action ready when needed.
    const actionParams = _getActionParams();
    if (actionParams && typeof actionParams.actionRequest === "number") {
        const { actionRequest, options } = actionParams;
        _loadAction(actionRequest, options.additionalContext);
    }

    env.bus.on("CLEAR-CACHES", null, () => {
        actionCache = {};
    });

    // ---------------------------------------------------------------------------
    // misc
    // ---------------------------------------------------------------------------

    /**
     * Removes the current dialog from the action service's state.
     * It returns the dialog's onClose callback to be able to propagate it to the next dialog.
     *
     * @return {Function|undefined} When there was a dialog, returns its onClose callback for propagation to next dialog.
     */
    function _removeDialog() {
        if (dialog) {
            const { onClose, remove } = dialog;
            dialog = null;
            // Remove the dialog from the dialog_service.
            // The code is well enough designed to avoid falling in a function call loop.
            remove();
            return onClose;
        }
    }

    /**
     * Returns the last controller of the current controller stack.
     *
     * @returns {Controller|null}
     */
    function _getCurrentController() {
        const stack = controllerStack;
        return stack.length ? stack[stack.length - 1] : null;
    }

    /**
     * Given an id, xmlid, tag (key of the client action registry) or directly an
     * object describing an action.
     *
     * @private
     * @param {ActionRequest} actionRequest
     * @param {Context} [context={}]
     * @returns {Promise<Action>}
     */
    async function _loadAction(actionRequest, context = {}) {
        if (typeof actionRequest === "string" && actionRegistry.contains(actionRequest)) {
            // actionRequest is a key in the actionRegistry
            return {
                target: "current",
                tag: actionRequest,
                type: "ir.actions.client",
            };
        }

        if (typeof actionRequest === "string" || typeof actionRequest === "number") {
            // actionRequest is an id or an xmlid
            const additional_context = {
                active_id: context.active_id,
                active_ids: context.active_ids,
                active_model: context.active_model,
            };
            const key = `${JSON.stringify(actionRequest)},${JSON.stringify(additional_context)}`;
            if (!actionCache[key]) {
                actionCache[key] = env.services.rpc("/web/action/load", {
                    action_id: actionRequest,
                    additional_context,
                });
            }
            const action = await actionCache[key];
            if (!action) {
                return {
                    type: "ir.actions.client",
                    tag: "invalid_action",
                    id: actionRequest,
                };
            }
            return Object.assign({}, action);
        }

        // actionRequest is an object describing the action
        return actionRequest;
    }

    /**
     * this function returns an action description
     * with a unique jsId.
     */
    function _preprocessAction(action, context = {}) {
        action._originalAction = JSON.stringify(action);
        action.context = makeContext([context, action.context], env.services.user.context);
        if (action.domain) {
            const domain = action.domain || [];
            action.domain =
                typeof domain === "string"
                    ? evaluateExpr(
                          domain,
                          Object.assign({}, env.services.user.context, action.context)
                      )
                    : domain;
        }
        action = { ...action }; // manipulate a copy to keep cached action unmodified
        action.jsId = `action_${++id}`;
        if (action.type === "ir.actions.act_window" || action.type === "ir.actions.client") {
            action.target = action.target || "current";
        }
        if (action.type === "ir.actions.act_window") {
            action.views = [...action.views]; // manipulate a copy to keep cached action unmodified
            action.controllers = {};
            const target = action.target;
            if (target !== "inline" && !(target === "new" && action.views[0][1] === "form")) {
                // FIXME: search view arch is already sent with load_action, so either remove it
                // from there or load all fieldviews alongside the action for the sake of consistency
                const searchViewId = action.search_view_id ? action.search_view_id[0] : false;
                action.views.push([searchViewId, "search"]);
            }
        }
        return action;
    }

    /**
     * @private
     * @param {string} viewType
     * @throws {Error} if the current controller is not a view
     * @returns {View | null}
     */
    function _getView(viewType) {
        const currentController = controllerStack[controllerStack.length - 1];
        if (currentController.action.type !== "ir.actions.act_window") {
            throw new Error(`switchView called but the current controller isn't a view`);
        }
        const view = currentController.views.find((view) => view.type === viewType);
        return view || null;
    }

    /**
     * Given a controller stack, returns the list of breadcrumb items.
     *
     * @private
     * @param {ControllerStack} stack
     * @returns {Breadcrumbs}
     */
    function _getBreadcrumbs(stack) {
        return stack
            .filter((controller) => controller.action.tag !== "menu")
            .map((controller) => {
                return {
                    jsId: controller.jsId,
                    name: controller.title || controller.action.name || env._t("Undefined"),
                };
            });
    }

    /**
     * @private
     * @returns {ActionParams | null}
     */
    function _getActionParams() {
        const state = env.services.router.current.hash;
        const options = { clearBreadcrumbs: true };
        let actionRequest = null;
        if (state.action) {
            // ClientAction
            if (actionRegistry.contains(state.action)) {
                actionRequest = {
                    params: state,
                    tag: state.action,
                    type: "ir.actions.client",
                };
            } else {
                // The action to load isn't the current one => executes it
                actionRequest = state.action;
                const context = { params: state };
                if (state.active_id) {
                    context.active_id = state.active_id;
                }
                if (state.active_ids) {
                    context.active_ids = parseActiveIds(state.active_ids);
                } else if (state.active_id) {
                    context.active_ids = [state.active_id];
                }
                Object.assign(options, {
                    additionalContext: context,
                    viewType: state.view_type,
                });
                if (state.id) {
                    options.props = { resId: state.id };
                }
            }
        } else if (state.model) {
            if (state.id) {
                actionRequest = {
                    res_model: state.model,
                    res_id: state.id,
                    type: "ir.actions.act_window",
                    views: [[state.view_id ? state.view_id : false, "form"]],
                };
            } else if (state.view_type) {
                // This is a window action on a multi-record view => restores it from
                // the session storage
                const storedAction = browser.sessionStorage.getItem("current_action");
                const lastAction = JSON.parse(storedAction || "{}");
                if (lastAction.res_model === state.model) {
                    actionRequest = lastAction;
                    options.viewType = state.view_type;
                }
            }
        }
        // If no action => falls back on the user default action (if any).
        if (!actionRequest && env.services.user.home_action_id) {
            actionRequest = env.services.user.home_action_id;
        }
        return actionRequest ? { actionRequest, options } : null;
    }

    /**
     * @param {ClientAction | ActWindowAction} action
     * @param {Object} props
     * @returns {{ props: ActionProps, config: Config }}
     */
    function _getActionInfo(action, props) {
        return {
            props: Object.assign({}, props, { action, actionId: action.id }),
            config: {
                actionId: action.id,
                actionType: action.type,
                actionFlags: action.flags,
                displayName: action.display_name || action.name || "",
                views: action.views,
            },
        };
    }

    /**
     * @param {Action} action
     * @returns {ActionMode}
     */
    function _getActionMode(action) {
        if (action.target === "new") {
            // No possible override for target="new"
            return "new";
        }
        if (action.type === "ir.actions.client") {
            const clientAction = actionRegistry.get(action.tag);
            if (clientAction.target) {
                // Target is forced by the definition of the client action
                return clientAction.target;
            }
        }
        if (controllerStack.some((c) => c.action.target === "fullscreen")) {
            // Force fullscreen when one of the controllers is set to fullscreen
            return "fullscreen";
        }
        // Default: current
        return "current";
    }

    /**
     * @private
     * @returns {SwitchViewParams | null}
     */
    function _getSwitchViewParams() {
        const state = env.services.router.current.hash;
        if (state.action && !actionRegistry.contains(state.action)) {
            const currentController = controllerStack[controllerStack.length - 1];
            const currentActionId =
                currentController && currentController.action && currentController.action.id;
            // Window Action: determines model, viewType etc....
            if (
                currentController &&
                currentController.action.type === "ir.actions.act_window" &&
                currentActionId === state.action
            ) {
                const props = { resId: state.id || false };
                const viewType = state.view_type || currentController.view.type;
                return { viewType, props };
            }
        }
        return null;
    }

    /**
     * @param {BaseView} view
     * @param {ActWindowAction} action
     * @param {BaseView[]} views
     * @param {Object} props
     * @returns {{ props: ViewProps, config: Config }}
     */
    function _getViewInfo(view, action, views, props = {}) {
        const target = action.target;
        const viewSwitcherEntries = views
            .filter((v) => v.multiRecord === view.multiRecord)
            .map((v) => {
                const viewSwitcherEntry = {
                    icon: v.icon,
                    name: v.display_name.toString(),
                    type: v.type,
                    multiRecord: v.multiRecord,
                };
                if (view.type === v.type) {
                    viewSwitcherEntry.active = true;
                }
                return viewSwitcherEntry;
            });
        const context = action.context || {};
        let groupBy = context.group_by || [];
        if (typeof groupBy === "string") {
            groupBy = [groupBy];
        }
        const viewProps = Object.assign({}, props, {
            context,
            display: { mode: target === "new" ? "inDialog" : target },
            domain: action.domain || [],
            groupBy,
            loadActionMenus: target !== "new" && target !== "inline",
            loadIrFilters: action.views.some((v) => v[1] === "search"),
            resModel: action.res_model,
            type: view.type,
        });

        if (target === "inline") {
            viewProps.searchMenuTypes = [];
        }

        const specialKeys = ["help", "useSampleModel", "limit", "count"];
        for (const key of specialKeys) {
            if (key in action) {
                if (key === "help") {
                    viewProps.noContentHelp = action.help;
                } else {
                    viewProps[key] = action[key];
                }
            }
        }

        if (context.active_id || context.active_ids || context.search_disable_custom_filters) {
            viewProps.activateFavorite = false; // not sure --> check logic
        }

        // view specific
        if (action.res_id) {
            viewProps.resId = action.res_id;
        }

        // LEGACY CODE COMPATIBILITY: remove when all views will be written in owl
        if (view.isLegacy) {
            const legacyActionInfo = { ...action, ...viewProps.action };
            Object.assign(viewProps, {
                action: legacyActionInfo,
                View: view,
                views: action.views,
            });
        }
        // END LEGACY CODE COMPATIBILITY

        return {
            props: viewProps,
            config: {
                actionId: action.id,
                actionType: action.type,
                actionFlags: action.flags,
                displayName: action.display_name || action.name || "",
                views: action.views,
                viewSwitcherEntries,
            },
        };
    }

    /**
     * Computes the position of the controller in the nextStack according to options
     * @param {Object} options
     * @param {boolean} [options.clearBreadcrumbs=false]
     * @param {'replaceLast' | 'replaceLastAction'} [options.stackPosition]
     * @param {number} [options.index]
     */
    function _computeStackIndex(options) {
        let index = null;
        if (options.clearBreadcrumbs) {
            index = 0;
        } else if (options.stackPosition === "replaceCurrentAction") {
            const currentController = controllerStack[controllerStack.length - 1];
            if (currentController) {
                index = controllerStack.findIndex(
                    (ct) => ct.action.jsId === currentController.action.jsId
                );
            }
        } else if (options.stackPosition === "replacePreviousAction") {
            let last;
            for (let i = controllerStack.length - 1; i >= 0; i--) {
                const action = controllerStack[i].action.jsId;
                if (!last) {
                    last = action;
                }
                if (action !== last) {
                    last = action;
                    break;
                }
            }
            if (last) {
                index = controllerStack.findIndex((ct) => ct.action.jsId === last);
            }
            // TODO: throw if there is no previous action?
        } else if ("index" in options) {
            index = options.index;
        } else {
            index = controllerStack.length;
        }
        return index;
    }

    /**
     * Triggers a re-rendering with respect to the given controller.
     *
     * @private
     * @param {Controller} controller
     * @param {UpdateStackOptions} options
     * @param {boolean} [options.clearBreadcrumbs=false]
     * @param {number} [options.index]
     * @returns {Promise<Number>}
     */
    async function _updateUI(controller, options = {}) {
        let resolve;
        let reject;
        let dialogCloseResolve;
        const currentActionProm = new Promise((_res, _rej) => {
            resolve = _res;
            reject = _rej;
        });
        const action = controller.action;
        const index = _computeStackIndex(options);
        const controllerArray = [controller];
        if (options.lazyController) {
            controllerArray.unshift(options.lazyController);
        }
        const nextStack = controllerStack.slice(0, index).concat(controllerArray);

        // Compute breadcrumbs
        if (action.target === "new") {
            controller.config.breadcrumbs = [];
        } else {
            controller.config.breadcrumbs = _getBreadcrumbs(nextStack.slice(0, -1));
        }
        if (controller.Component.isLegacy) {
            controller.props.breadcrumbs = controller.config.breadcrumbs;
        }

        class ControllerComponent extends Component {
            setup() {
                this.Component = controller.Component;
                this.componentRef = useRef("component");
                this.titleService = useService("title");
                useDebugCategory("action", { action });
                useSubEnv({ config: controller.config });
                if (action.target !== "new") {
                    this.__beforeLeave__ = new CallbackRecorder();
                    this.__getGlobalState__ = new CallbackRecorder();
                    this.__getLocalState__ = new CallbackRecorder();
                    useBus(env.bus, "CLEAR-UNCOMMITTED-CHANGES", (callbacks) => {
                        const beforeLeaveFns = this.__beforeLeave__.callbacks;
                        callbacks.push(...beforeLeaveFns);
                    });
                    useSubEnv({
                        __beforeLeave__: this.__beforeLeave__,
                        __getGlobalState__: this.__getGlobalState__,
                        __getLocalState__: this.__getLocalState__,
                    });
                }
                this.isMounted = false;
            }
            catchError(error) {
                reject(error);
                cleanDomFromBootstrap();
                if (action.target === "new") {
                    // get the dialog service to close the dialog.
                    throw error;
                } else {
                    const lastCt = controllerStack[controllerStack.length - 1];
                    let info = {};
                    if (lastCt) {
                        if (lastCt.jsId === controller.jsId) {
                            // the error occurred on the controller which is
                            // already in the DOM, so simply show the error
                            Promise.resolve().then(() => {
                                throw error;
                            });
                            return;
                        } else {
                            info = lastCt.__info__;
                            // the error occurred while rendering a new controller,
                            // so go back to the last non faulty controller
                            // (the error will be shown anyway as the promise
                            // has been rejected)
                        }
                    }
                    env.bus.trigger("ACTION_MANAGER:UPDATE", info);
                }
            }
            mounted() {
                if (action.target === "new") {
                    dialogCloseProm = new Promise((_r) => {
                        dialogCloseResolve = _r;
                    }).then(() => {
                        dialogCloseProm = undefined;
                    });
                    dialog = nextDialog;
                } else {
                    controller.getGlobalState = () => {
                        const exportFns = this.__getGlobalState__.callbacks;
                        if (exportFns.length) {
                            return Object.assign({}, ...exportFns.map((fn) => fn()));
                        }
                    };
                    controller.getLocalState = () => {
                        const exportFns = this.__getLocalState__.callbacks;
                        if (exportFns.length) {
                            return Object.assign({}, ...exportFns.map((fn) => fn()));
                        }
                    };

                    // LEGACY CODE COMPATIBILITY: remove when controllers will be written in owl
                    // we determine here which actions no longer occur in the nextStack,
                    // and we manually destroy all their controller's widgets
                    const nextStackActionIds = nextStack.map((c) => c.action.jsId);
                    const toDestroy = new Set();
                    for (const c of controllerStack) {
                        if (!nextStackActionIds.includes(c.action.jsId)) {
                            if (c.action.type === "ir.actions.act_window") {
                                for (const viewType in c.action.controllers) {
                                    const controller = c.action.controllers[viewType];
                                    if (controller.Component.isLegacy) {
                                        toDestroy.add(controller);
                                    }
                                }
                            } else {
                                toDestroy.add(c);
                            }
                        }
                    }
                    for (const c of toDestroy) {
                        if (c.exportedState && c.exportedState.__legacy_widget__) {
                            c.exportedState.__legacy_widget__.destroy();
                        }
                    }
                    // END LEGACY CODE COMPATIBILITY
                    controllerStack = nextStack; // the controller is mounted, commit the new stack
                    pushState(controller);
                    this.titleService.setParts({
                        action: controller.title || this.env.config.displayName,
                    });
                    browser.sessionStorage.setItem("current_action", action._originalAction);
                }
                resolve();
                env.bus.trigger("ACTION_MANAGER:UI-UPDATED", _getActionMode(action));
                this.isMounted = true;
            }
            willUnmount() {
                if (action.target === "new" && dialogCloseResolve) {
                    dialogCloseResolve();
                }
            }
            onHistoryBack() {
                const previousController = controllerStack[controllerStack.length - 2];
                if (previousController && !dialog) {
                    restore(previousController.jsId);
                } else {
                    _executeCloseAction();
                }
            }
            onTitleUpdated(ev) {
                controller.title = ev.detail;
                if (this.isMounted) {
                    // if not mounted yet, will be done in "mounted"
                    this.titleService.setParts({ action: controller.title });
                }
            }
        }
        ControllerComponent.template = ControllerComponentTemplate;
        ControllerComponent.Component = controller.Component;

        let nextDialog = null;
        if (action.target === "new") {
            cleanDomFromBootstrap();
            const actionDialogProps = {
                // TODO add size
                ActionComponent: ControllerComponent,
                actionProps: controller.props,
            };
            if (action.name) {
                actionDialogProps.title = action.name;
            }

            let onClose = _removeDialog();
            const removeDialog = env.services.dialog.add(ActionDialog, actionDialogProps, {
                onClose: () => {
                    const onClose = _removeDialog();
                    if (onClose) {
                        onClose();
                    }
                    cleanDomFromBootstrap();
                },
            });
            nextDialog = {
                remove: removeDialog,
                onClose: onClose || options.onClose,
            };
            return currentActionProm;
        }

        const currentController = _getCurrentController();
        if (currentController && currentController.getLocalState) {
            currentController.exportedState = currentController.getLocalState();
        }
        if (controller.exportedState) {
            controller.props.state = controller.exportedState;
        }

        // TODO DAM Remarks:
        // this thing seems useless for client actions.
        // restore and switchView (at least) use this --> cannot be done in switchView only
        // if prop globalState has been passed in doAction, since the action is new the prop won't be overridden in l655.
        // if globalState is not useful for client actions --> maybe use that thing in useSetupView instead of useSetupAction?
        // a good thing: the Object.assign seems to reflect the use of "externalState" in legacy Model class --> things should be fine.
        if (currentController && currentController.getGlobalState) {
            currentController.action.globalState = Object.assign(
                {},
                currentController.action.globalState,
                currentController.getGlobalState() // what if this = {}?
            );
        }
        if (controller.action.globalState) {
            controller.props.globalState = controller.action.globalState;
        }

        const closingProm = _executeCloseAction();

        controller.__info__ = {
            id: ++id,
            Component: ControllerComponent,
            componentProps: controller.props,
        };
        env.bus.trigger("ACTION_MANAGER:UPDATE", controller.__info__);
        return Promise.all([currentActionProm, closingProm]).then((r) => r[0]);
    }

    // ---------------------------------------------------------------------------
    // ir.actions.act_url
    // ---------------------------------------------------------------------------

    /**
     * Executes actions of type 'ir.actions.act_url', i.e. redirects to the
     * given url.
     *
     * @private
     * @param {ActURLAction} action
     * @param {ActionOptions} options
     */
    function _executeActURLAction(action, options) {
        if (action.target === "self") {
            env.services.router.redirect(action.url);
        } else {
            const w = browser.open(action.url, "_blank");
            if (!w || w.closed || typeof w.closed === "undefined") {
                const msg = env._t(
                    "A popup window has been blocked. You may need to change your " +
                        "browser settings to allow popup windows for this page."
                );
                env.services.notification.add(msg, {
                    sticky: true,
                    type: "warning",
                });
            }
            if (options.onClose) {
                options.onClose();
            }
        }
    }

    // ---------------------------------------------------------------------------
    // ir.actions.act_window
    // ---------------------------------------------------------------------------

    /**
     * Executes an action of type 'ir.actions.act_window'.
     *
     * @private
     * @param {ActWindowAction} action
     * @param {ActionOptions} options
     */
    function _executeActWindowAction(action, options) {
        const views = [];
        for (const [, type] of action.views) {
            if (viewRegistry.contains(type)) {
                views.push(viewRegistry.get(type));
            }
        }
        if (!views.length) {
            throw new Error(`No view found for act_window action ${action.id}`);
        }

        let view = options.viewType && views.find((v) => v.type === options.viewType);
        let lazyView;

        if (view && !view.multiRecord) {
            lazyView = views[0].multiRecord ? views[0] : undefined;
        } else if (!view) {
            view = views[0];
        }

        if (env.isSmall) {
            if (!view.isMobileFriendly) {
                view = _findMobileView(views, view.multiRecord) || view;
            }
            if (lazyView && !lazyView.isMobileFriendly) {
                lazyView = _findMobileView(views, lazyView.multiRecord) || lazyView;
            }
        }

        const controller = {
            jsId: `controller_${++id}`,
            Component: view.isLegacy ? view : View,
            action,
            view,
            views,
            ..._getViewInfo(view, action, views, options.props),
        };
        action.controllers[view.type] = controller;

        const updateUIOptions = {
            clearBreadcrumbs: options.clearBreadcrumbs,
            onClose: options.onClose,
            stackPosition: options.stackPosition,
        };

        if (lazyView) {
            updateUIOptions.lazyController = {
                jsId: `controller_${++id}`,
                Component: lazyView.isLegacy ? lazyView : View,
                action,
                view: lazyView,
                views,
                ..._getViewInfo(lazyView, action, views),
            };
        }

        return _updateUI(controller, updateUIOptions);
    }

    /**
     * Helper function to find the first mobile-friendly view, if any.
     *
     * @private
     * @param {Array} views an array of views
     * @param {boolean} multiRecord true if we search for a multiRecord view
     * @returns {Object|undefined} first mobile-friendly view found
     */
    function _findMobileView(views, multiRecord) {
        return views.find((view) => view.isMobileFriendly && view.multiRecord === multiRecord);
    }

    // ---------------------------------------------------------------------------
    // ir.actions.client
    // ---------------------------------------------------------------------------

    /**
     * Executes an action of type 'ir.actions.client'.
     *
     * @private
     * @param {ClientAction} action
     * @param {ActionOptions} options
     */
    async function _executeClientAction(action, options) {
        const clientAction = actionRegistry.get(action.tag);
        if (clientAction.prototype instanceof Component) {
            if (action.target !== "new") {
                await clearUncommittedChanges(env);
                if (clientAction.target) {
                    action.target = clientAction.target;
                }
            }
            const controller = {
                jsId: `controller_${++id}`,
                Component: clientAction,
                action,
                ..._getActionInfo(action, options.props),
            };
            return _updateUI(controller, {
                clearBreadcrumbs: options.clearBreadcrumbs,
                stackPosition: options.stackPosition,
                onClose: options.onClose,
            });
        } else {
            const next = await clientAction(env, action);
            if (next) {
                return doAction(next, options);
            }
        }
    }

    // ---------------------------------------------------------------------------
    // ir.actions.report
    // ---------------------------------------------------------------------------

    // messages that might be shown to the user dependening on the state of wkhtmltopdf
    const link = '<br><br><a href="http://wkhtmltopdf.org/" target="_blank">wkhtmltopdf.org</a>';
    const WKHTMLTOPDF_MESSAGES = {
        broken:
            env._t(
                "Your installation of Wkhtmltopdf seems to be broken. The report will be shown " +
                    "in html."
            ) + link,
        install:
            env._t(
                "Unable to find Wkhtmltopdf on this system. The report will be shown in " + "html."
            ) + link,
        upgrade:
            env._t(
                "You should upgrade your version of Wkhtmltopdf to at least 0.12.0 in order to " +
                    "get a correct display of headers and footers as well as support for " +
                    "table-breaking between pages."
            ) + link,
        workers: env._t(
            "You need to start Odoo with at least two workers to print a pdf version of " +
                "the reports."
        ),
    };

    // only check the wkhtmltopdf state once, so keep the rpc promise
    let wkhtmltopdfStateProm;

    /**
     * Generates the report url given a report action.
     *
     * @private
     * @param {ReportAction} action
     * @param {ReportType} type
     * @returns {string}
     */
    function _getReportUrl(action, type) {
        let url = `/report/${type}/${action.report_name}`;
        const actionContext = action.context || {};
        if (action.data && JSON.stringify(action.data) !== "{}") {
            // build a query string with `action.data` (it's the place where reports
            // using a wizard to customize the output traditionally put their options)
            const options = encodeURIComponent(JSON.stringify(action.data));
            const context = encodeURIComponent(JSON.stringify(actionContext));
            url += `?options=${options}&context=${context}`;
        } else {
            if (actionContext.active_ids) {
                url += `/${actionContext.active_ids.join(",")}`;
            }
            if (type === "html") {
                const context = encodeURIComponent(JSON.stringify(env.services.user.context));
                url += `?context=${context}`;
            }
        }
        return url;
    }

    /**
     * Launches download action of the report
     *
     * @private
     * @param {ReportAction} action
     * @param {ActionOptions} options
     * @returns {Promise}
     */
    async function _triggerDownload(action, options, type) {
        const url = _getReportUrl(action, type);
        env.services.ui.block();
        try {
            await download({
                url: "/report/download",
                data: {
                    data: JSON.stringify([url, action.report_type]),
                    context: JSON.stringify(env.services.user.context),
                },
            });
        } finally {
            env.services.ui.unblock();
        }
        const onClose = options.onClose;
        if (action.close_on_report_download) {
            return doAction({ type: "ir.actions.act_window_close" }, { onClose });
        } else if (onClose) {
            onClose();
        }
    }

    function _executeReportClientAction(action, options) {
        const props = Object.assign({}, options.props, {
            data: action.data,
            display_name: action.display_name,
            name: action.name,
            report_file: action.report_file,
            report_name: action.report_name,
            report_url: _getReportUrl(action, "html"),
            context: Object.assign({}, action.context),
        });

        const controller = {
            jsId: `controller_${++id}`,
            // for historical reasons, the report Component is a client action,
            // but there's no need to keep this when it will be converted to owl.
            Component: actionRegistry.get("report.client_action"),
            action,
            ..._getActionInfo(action, props),
        };

        return _updateUI(controller, {
            clearBreadcrumbs: options.clearBreadcrumbs,
            stackPosition: options.stackPosition,
            onClose: options.onClose,
        });
    }

    /**
     * Executes actions of type 'ir.actions.report'.
     *
     * @private
     * @param {ReportAction} action
     * @param {ActionOptions} options
     */
    async function _executeReportAction(action, options) {
        const handlers = registry.category("ir.actions.report handlers").getAll();
        for (const handler of handlers) {
            const result = await handler(action, options, env);
            if (result) {
                return result;
            }
        }
        if (action.report_type === "qweb-html") {
            return _executeReportClientAction(action, options);
        } else if (action.report_type === "qweb-pdf") {
            // check the state of wkhtmltopdf before proceeding
            if (!wkhtmltopdfStateProm) {
                wkhtmltopdfStateProm = env.services.rpc("/report/check_wkhtmltopdf");
            }
            const state = await wkhtmltopdfStateProm;
            // display a notification according to wkhtmltopdf's state
            if (state in WKHTMLTOPDF_MESSAGES) {
                env.services.notification.add(WKHTMLTOPDF_MESSAGES[state], {
                    sticky: true,
                    title: env._t("Report"),
                });
            }
            if (state === "upgrade" || state === "ok") {
                // trigger the download of the PDF report
                return _triggerDownload(action, options, "pdf");
            } else {
                // open the report in the client action if generating the PDF is not possible
                return _executeReportClientAction(action, options);
            }
        } else if (action.report_type === "qweb-text") {
            return _triggerDownload(action, options, "text");
        } else {
            console.error(
                `The ActionManager can't handle reports of type ${action.report_type}`,
                action
            );
        }
    }

    // ---------------------------------------------------------------------------
    // ir.actions.server
    // ---------------------------------------------------------------------------

    /**
     * Executes an action of type 'ir.actions.server'.
     *
     * @private
     * @param {ServerAction} action
     * @param {ActionOptions} options
     * @returns {Promise<void>}
     */
    async function _executeServerAction(action, options) {
        const runProm = env.services.rpc("/web/action/run", {
            action_id: action.id,
            context: makeContext([env.services.user.context, action.context]),
        });
        let nextAction = await keepLast.add(runProm);
        nextAction = nextAction || { type: "ir.actions.act_window_close" };
        return doAction(nextAction, options);
    }

    async function _executeCloseAction(params = {}) {
        let onClose;
        if (dialog) {
            onClose = _removeDialog();
        } else {
            onClose = params.onClose;
        }
        if (onClose) {
            await onClose(params.onCloseInfo);
        }

        return dialogCloseProm;
    }

    // ---------------------------------------------------------------------------
    // public API
    // ---------------------------------------------------------------------------

    /**
     * Main entry point of a 'doAction' request. Loads the action and executes it.
     *
     * @param {ActionRequest} actionRequest
     * @param {ActionOptions} options
     * @returns {Promise<number | undefined | void>}
     */
    async function doAction(actionRequest, options = {}) {
        const actionProm = _loadAction(actionRequest, options.additionalContext);
        let action = await keepLast.add(actionProm);
        action = _preprocessAction(action, options.additionalContext);
        options.clearBreadcrumbs = action.target === "main" || options.clearBreadcrumbs;
        switch (action.type) {
            case "ir.actions.act_url":
                return _executeActURLAction(action, options);
            case "ir.actions.act_window":
                if (action.target !== "new") {
                    await clearUncommittedChanges(env);
                }
                return _executeActWindowAction(action, options);
            case "ir.actions.act_window_close":
                return _executeCloseAction({ onClose: options.onClose, onCloseInfo: action.infos });
            case "ir.actions.client":
                return _executeClientAction(action, options);
            case "ir.actions.report":
                return _executeReportAction(action, options);
            case "ir.actions.server":
                return _executeServerAction(action, options);
            default: {
                let handler = actionHandlersRegistry.get(action.type, null);
                if (handler !== null) {
                    return handler({ env, action, options });
                }
                throw new Error(
                    `The ActionManager service can't handle actions of type ${action.type}`
                );
            }
        }
    }

    /**
     * Executes an action on top of the current one (typically, when a button in a
     * view is clicked). The button may be of type 'object' (call a given method
     * of a given model) or 'action' (execute a given action). Alternatively, the
     * button may have the attribute 'special', and in this case an
     * 'ir.actions.act_window_close' is executed.
     *
     * @param {DoActionButtonParams} params
     * @returns {Promise<void>}
     */
    async function doActionButton(params) {
        // determine the action to execute according to the params
        let action;
        const context = makeContext([params.context, params.buttonContext]);
        if (params.special) {
            action = { type: "ir.actions.act_window_close", infos: { special: true } };
        } else if (params.type === "object") {
            // call a Python Object method, which may return an action to execute
            let args = params.resId ? [[params.resId]] : [params.resIds];
            if (params.args) {
                let additionalArgs;
                try {
                    // warning: quotes and double quotes problem due to json and xml clash
                    // maybe we should force escaping in xml or do a better parse of the args array
                    additionalArgs = JSON.parse(params.args.replace(/'/g, '"'));
                } catch (e) {
                    browser.console.error("Could not JSON.parse arguments", params.args);
                }
                args = args.concat(additionalArgs);
            }
            const callProm = env.services.rpc("/web/dataset/call_button", {
                args,
                kwargs: { context },
                method: params.name,
                model: params.resModel,
            });
            action = await keepLast.add(callProm);
            action =
                action && typeof action === "object"
                    ? action
                    : { type: "ir.actions.act_window_close" };
        } else if (params.type === "action") {
            // execute a given action, so load it first
            context.active_id = params.resId || null;
            context.active_ids = params.resIds;
            context.active_model = params.resModel;
            action = await keepLast.add(_loadAction(params.name, context));
        } else {
            throw new InvalidButtonParamsError("Missing type for doActionButton request");
        }
        // filter out context keys that are specific to the current action, because:
        //  - wrong default_* and search_default_* values won't give the expected result
        //  - wrong group_by values will fail and forbid rendering of the destination view
        let currentCtx = {};
        for (const key in params.context) {
            if (key.match(CTX_KEY_REGEX) === null) {
                currentCtx[key] = params.context[key];
            }
        }
        const activeCtx = { active_model: params.resModel };
        if (params.resId) {
            activeCtx.active_id = params.resId;
            activeCtx.active_ids = [params.resId];
        }
        action.context = makeContext([currentCtx, params.buttonContext, activeCtx, action.context]);
        // in case an effect is returned from python and there is already an effect
        // attribute on the button, the priority is given to the button attribute
        const effect = params.effect ? evaluateExpr(params.effect) : action.effect;
        const options = { onClose: params.onClose };
        await doAction(action, options);
        if (params.close) {
            await _executeCloseAction();
        }
        if (effect) {
            env.services.effect.add(effect);
        }
    }

    /**
     * Switches to the given view type in action of the last controller of the
     * stack. This action must be of type 'ir.actions.act_window'.
     *
     * @param {ViewType} viewType
     * @param {Object} [props={}]
     * @throws {ViewNotFoundError} if the viewType is not found on the current action
     * @returns {Promise<Number>}
     */
    async function switchView(viewType, props = {}) {
        if (dialog) {
            // we don't want to switch view when there's a dialog open, as we would
            // not switch in the correct action (action in background != dialog action)
            return;
        }
        const controller = controllerStack[controllerStack.length - 1];
        const view = _getView(viewType);
        if (!view) {
            throw new ViewNotFoundError(
                sprintf(
                    env._t("No view of type '%s' could be found in the current action."),
                    viewType
                )
            );
        }
        await keepLast.add(Promise.resolve());
        const newController = controller.action.controllers[viewType] || {
            jsId: `controller_${++id}`,
            Component: view.isLegacy ? view : View,
            action: controller.action,
            views: controller.views,
            view,
        };

        // LEGACY CODE COMPATIBILITY: remove when controllers will be written in owl
        if (view.isLegacy && newController.jsId === controller.jsId) {
            // case where a legacy view is reloaded via the view switcher
            const { __legacy_widget__ } = controller.getLocalState();
            const params = {};
            if ("resId" in props) {
                params.currentId = props.resId;
            }
            return __legacy_widget__.reload(params);
        }
        // END LEGACY CODE COMPATIBILITY

        Object.assign(
            newController,
            _getViewInfo(view, controller.action, controller.views, props)
        );
        controller.action.controllers[viewType] = newController;
        let index;
        if (view.multiRecord) {
            index = controllerStack.findIndex((ct) => ct.action.jsId === controller.action.jsId);
            index = index > -1 ? index : controllerStack.length - 1;
        } else {
            // This case would mostly happen when loadState detects a change in the URL.
            // Also, I guess we may need it when we have other monoRecord views
            index = controllerStack.findIndex(
                (ct) => ct.action.jsId === controller.action.jsId && !ct.view.multiRecord
            );
            index = index > -1 ? index : controllerStack.length;
        }
        await clearUncommittedChanges(env);
        return _updateUI(newController, { index });
    }

    /**
     * Restores a controller from the controller stack given its id. Typically,
     * this function is called when clicking on the breadcrumbs. If no id is given
     * restores the previous controller from the stack (penultimate).
     *
     * @param {string} jsId
     */
    async function restore(jsId) {
        await keepLast.add(Promise.resolve());
        let index;
        if (!jsId) {
            index = controllerStack.length - 2;
        } else {
            index = controllerStack.findIndex((controller) => controller.jsId === jsId);
        }
        if (index < 0) {
            const msg = jsId ? "Invalid controller to restore" : "No controller to restore";
            throw new ControllerNotFoundError(msg);
        }
        const controller = controllerStack[index];
        if (controller.action.type === "ir.actions.act_window") {
            Object.assign(
                controller,
                _getViewInfo(controller.view, controller.action, controller.views)
            );
        }
        await clearUncommittedChanges(env);
        return _updateUI(controller, { index });
    }

    /**
     * Performs a "doAction" or a "switchView" according to the current content of
     * the URL. The id of the underlying action is be returned if one of these
     * operations has successfully started.
     *
     * @returns {Promise<boolean>} true iff the state could have been loaded
     */
    async function loadState() {
        const switchViewParams = _getSwitchViewParams();
        if (switchViewParams) {
            // only when we already have an action in dom
            const { viewType, props } = switchViewParams;
            const view = _getView(viewType);
            if (view) {
                // Params valid and view found => performs a "switchView"
                await switchView(viewType, props);
                return true;
            }
        } else {
            const actionParams = _getActionParams();
            if (actionParams) {
                // Params valid => performs a "doAction"
                const { actionRequest, options } = actionParams;
                await doAction(actionRequest, options);
                return true;
            }
        }
        return false;
    }

    function pushState(controller) {
        const newState = {};
        const action = controller.action;
        if (action.id) {
            newState.action = action.id;
        } else if (action.type === "ir.actions.client") {
            newState.action = action.tag;
        }
        if (action.context) {
            const activeId = action.context.active_id;
            if (activeId) {
                newState.active_id = activeId;
            }
            const activeIds = action.context.active_ids;
            // we don't push active_ids if it's a single element array containing
            // the active_id to make the url shorter in most cases
            if (activeIds && !(activeIds.length === 1 && activeIds[0] === activeId)) {
                newState.active_ids = activeIds.join(",");
            }
        }
        if (action.type === "ir.actions.act_window") {
            const props = controller.props;
            newState.model = props.resModel;
            newState.view_type = props.type;
            newState.id = props.resId || (props.state && props.state.currentId) || undefined;
        }
        env.services.router.pushState(newState, { replace: true });
    }
    return {
        doAction,
        doActionButton,
        switchView,
        restore,
        loadState,
        async loadAction(actionRequest, context) {
            let action = await _loadAction(actionRequest, context);
            return _preprocessAction(action, context);
        },
        get currentController() {
            return _getCurrentController();
        },
        __legacy__isActionInStack(actionId) {
            return controllerStack.find((c) => c.action.jsId === actionId);
        },
    };
}

export const actionService = {
    dependencies: ["effect", "localization", "notification", "router", "rpc", "ui", "user"],
    start(env) {
        return makeActionManager(env);
    },
};

registry.category("services").add("action", actionService);
