// @ts-check

/** @module @web/webclient/actions/action_service - Action manager that routes server/client actions to views, dialogs, and URL redirects */

import {
    Component,
    markup,
    onError,
    onMounted,
    onWillUnmount,
    reactive,
    status,
    useChildSubEnv,
    xml,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { router as _router } from "@web/core/browser/router";
import { makeContext } from "@web/core/context";
import { _t } from "@web/core/l10n/translation";
import { rpc, rpcBus } from "@web/core/network/rpc";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/collections/objects";
import { Deferred, KeepLast } from "@web/core/utils/concurrency";
import { isHtmlEmpty } from "@web/core/utils/dom/html";
import { useBus, useService } from "@web/core/utils/hooks";
import { CallbackRecorder } from "@web/search/action_hook";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { useDebugCategory } from "@web/services/debug/debug_context";
import { UPDATE_METHODS } from "@web/services/orm_service";
import { user } from "@web/services/user";
import { View, ViewNotFoundError } from "@web/views/view";

import { executeActionButton } from "./action_button_executor";
import { DIALOG_SIZES } from "./action_constants";
import { ActionDialog } from "./action_dialog";
import {
    buildActionInfo,
    buildActionViews,
    buildViewInfo,
} from "./action_info_builders";
import { getActionParams, makeActionState } from "./action_state";
import { findView, getActionMode } from "./action_views";
import { buildBreadcrumbs, controllersFromState } from "./breadcrumb_manager";
import { executeReportAction } from "./reports/report_executor";
import { SkeletonView } from "./skeleton_view";

class BlankComponent extends Component {
    static props = ["onMounted", "withControlPanel", "*"];
    static template = "web.BlankComponent";
    static components = { ControlPanel };

    setup() {
        useChildSubEnv({ config: { breadcrumbs: [], noBreadcrumbs: true } });
        onMounted(() => this.props.onMounted());
    }
}

const actionHandlersRegistry = registry.category("action_handlers");
const actionRegistry = registry.category("actions");

/** @typedef {number|false} ActionId */
/** @typedef {Object} ActionDescription */
/** @typedef {"current" | "fullscreen" | "new" | "main" | "self"} ActionMode */
/** @typedef {string} ActionTag */
/** @typedef {string} ActionXMLId */
/** @typedef {Object} Context */
/** @typedef {Function} CallableFunction */
/** @typedef {string} ViewType */

/** @typedef {ActionId|ActionXMLId|ActionTag|ActionDescription} ActionRequest */

/** @typedef {Object} Action */
/** @typedef {Action & { type: "ir.actions.act_window" }} ActWindowAction */
/** @typedef {Action & { type: "ir.actions.act_url" }} ActURLAction */
/** @typedef {Action & { type: "ir.actions.client" }} ClientAction */
/** @typedef {Action & { type: "ir.actions.server" }} ServerAction */
/** @typedef {Object} Controller */
/** @typedef {Object} BaseView */
/** @typedef {Object} ActionProps */
/** @typedef {Object} Config */
/** @typedef {Object} UpdateStackOptions */
/** @typedef {Object} DoActionButtonParams */

/**
 * @typedef {Object} ActionOptions
 * @property {Context} [additionalContext]
 * @property {boolean} [clearBreadcrumbs]
 * @property {CallableFunction} [onClose]
 * @property {Object} [props]
 * @property {ViewType} [viewType]
 * @property {"replaceCurrentAction" | "replacePreviousAction"} [stackPosition]
 * @property {number} [index]
 * @property {boolean} [newWindow]
 * @property {boolean} [forceLeave]
 * @property {Object[]} [newStack]
 * @property {boolean} [noEmptyTransition]
 * @property {Function} [onActionReady]
 */

export async function clearUncommittedChanges(
    env,
    { forceLeave } = /** @type {any} */ ({}),
) {
    const callbacks = [];
    env.bus.trigger("CLEAR-UNCOMMITTED-CHANGES", callbacks);
    const res = await Promise.all(callbacks.map((fn) => fn({ forceLeave })));
    return !res.includes(false);
}

export const standardActionServiceProps = {
    action: Object, // prop added by _getActionInfo
    actionId: { type: Number, optional: true }, // prop added by _getActionInfo
    className: { type: String, optional: true }, // prop added by the ActionContainer
    globalState: { type: Object, optional: true }, // prop added by _updateUI
    state: { type: Object, optional: true }, // prop added by _updateUI
    resId: { type: [Number, Boolean], optional: true },
    updateActionState: { type: Function, optional: true },
};

// -----------------------------------------------------------------------------
// Errors
// -----------------------------------------------------------------------------

export class ControllerNotFoundError extends Error {}

// -----------------------------------------------------------------------------
// ActionManager (Service)
// -----------------------------------------------------------------------------

// only register this template once for all dynamic classes ControllerComponent
const ControllerComponentTemplate = xml`<t t-component="Component" t-props="componentProps"/>`;

export function makeActionManager(env, router = _router) {
    const breadcrumbCache = {};
    const keepLast = new KeepLast();
    let id = 0;
    let controllerStack = [];
    let dialog = null;
    let nextDialog = null;

    router.hideKeyFromUrl("globalState");

    rpcBus.addEventListener("RPC:RESPONSE", async (ev) => {
        const { model, method } = ev.detail.data.params;
        if (model === "ir.actions.act_window" && UPDATE_METHODS.includes(method)) {
            rpcBus.trigger("CLEAR-CACHES", "/web/action/load");
            const virtualStack = await _controllersFromState(router.current);
            const nextStack = [...virtualStack, controllerStack.at(-1)];
            nextStack
                .at(-1)
                .config.breadcrumbs.splice(
                    0,
                    nextStack.at(-1).config.breadcrumbs.length,
                    ..._getBreadcrumbs(nextStack),
                );
            controllerStack = nextStack;
        }
    });

    // ---------------------------------------------------------------------------
    // misc
    // ---------------------------------------------------------------------------

    /** Breadcrumb context shared with extracted breadcrumb_manager module. */
    const breadcrumbCtx = {
        get sessionStorage() {
            return browser.sessionStorage;
        },
        stateToUrl: (s) => router.stateToUrl(s),
        makeController: _makeController,
        actionRegistry,
        breadcrumbCache,
    };

    async function _controllersFromState(state) {
        return controllersFromState(state, breadcrumbCtx);
    }

    /**
     * Removes the current dialog from the action service's state.
     * It returns the dialog's onClose callback to be able to propagate it to the next dialog.
     *
     * @return {Promise<void>}
     */
    async function _removeDialog(closeParams) {
        if (dialog) {
            const { onClose, remove } = dialog;
            await onClose?.(closeParams);
            dialog = null;
            // Remove the dialog from the dialog_service.
            // The code is well enough designed to avoid falling in a function call loop.
            remove();
        }
    }

    /**
     * Returns the last controller of the current controller stack.
     *
     * @returns {Controller|null}
     */
    function _getCurrentController() {
        const stack = controllerStack;
        return stack.length ? stack.at(-1) : null;
    }

    /**
     * Returns the current action, which is the action of the last controller in the stack.
     *
     * @returns {Promise<any>}
     */

    async function _getCurrentAction() {
        const currentController = _getCurrentController();
        let action = null;
        if (currentController) {
            if (currentController.virtual) {
                try {
                    action = await _loadAction(currentController.action.id);
                } catch (error) {
                    if (
                        error.exceptionName ===
                        "odoo.addons.web.controllers.action.MissingActionError"
                    ) {
                        action = null;
                    } else {
                        throw error;
                    }
                }
            } else {
                action = JSON.parse(currentController.action._originalAction);
            }
        }
        return action;
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
        if (
            typeof actionRequest === "string" &&
            actionRegistry.contains(actionRequest)
        ) {
            // actionRequest is a key in the actionRegistry
            return {
                target: "current",
                tag: actionRequest,
                type: "ir.actions.client",
            };
        }

        if (typeof actionRequest === "string" || typeof actionRequest === "number") {
            // actionRequest is an id or an xmlid
            const ctx = makeContext([user.context, context]);
            delete ctx.params;
            const action = await rpc(
                "/web/action/load",
                {
                    action_id: actionRequest,
                    context: ctx,
                },
                { cache: { type: "disk" } },
            );
            if (action.help) {
                action.help = markup(action.help);
            }
            return { ...action };
        }

        // actionRequest is an object describing the action
        return actionRequest;
    }

    /**
     * Makes a controller from the given params.
     *
     * @param {Object} params
     * @returns {Controller}
     */
    function _makeController(params) {
        return {
            ...params,
            jsId: `controller_${++id}`,
            isMounted: false,
        };
    }

    /**
     * this function returns an action description
     * with a unique jsId.
     */
    function _preprocessAction(action, context = {}) {
        try {
            delete action._originalAction;
            action._originalAction = JSON.stringify(action);
        } catch {
            // do nothing, the action might simply not be serializable
        }
        action.context = makeContext([context, action.context], user.context);
        const domain = action.domain || [];
        action.domain =
            typeof domain === "string"
                ? evaluateExpr(domain, { ...user.context, ...action.context })
                : domain;
        if (action.help) {
            if (isHtmlEmpty(action.help)) {
                delete action.help;
            }
        }
        action = { ...action }; // manipulate a copy to keep cached action unmodified
        action.jsId = `action_${++id}`;
        if (
            action.type === "ir.actions.act_window" ||
            action.type === "ir.actions.client"
        ) {
            action.target = action.target || "current";
        }
        if (action.type === "ir.actions.act_window") {
            action.views = [...action.views.map((v) => [v[0], v[1]])]; // manipulate a copy to keep cached action unmodified
            action.controllers = {};
            if (action.views.every((v) => ["form", "search"].includes(v[1]))) {
                action.views = action.views.filter((v) => v[1] === "form");
            } else {
                const searchViewId = action.search_view_id
                    ? action.search_view_id[0]
                    : false;
                action.views.push([searchViewId, "search"]);
            }
            if ("no_breadcrumbs" in action.context) {
                action._noBreadcrumbs = action.context.no_breadcrumbs;
                delete action.context.no_breadcrumbs;
            }
        }
        return action;
    }

    /**
     * @private
     * @param {string} viewType
     * @throws {Error} if the current controller is not a view
     * @returns {any}
     */
    function _getView(viewType) {
        const currentController = controllerStack.at(-1);
        if (currentController.action.type !== "ir.actions.act_window") {
            throw new Error(
                `switchView called but the current controller isn't a view`,
            );
        }
        const view = currentController.views.find((view) => view.type === viewType);
        return view || null;
    }

    function _getBreadcrumbs(stack) {
        return buildBreadcrumbs(stack, {
            stateToUrl: (s) => router.stateToUrl(s),
            restore,
        });
    }

    /**
     * Reconstruct an action request from URL state.
     * Delegates to the extracted getActionParams in action_state.
     */
    function _getActionParams(state) {
        return getActionParams(state);
    }

    /**
     * @param {ClientAction} action
     * @param {Object} props
     * @returns {{ props: ActionProps, config: Config }}
     */
    function _getActionInfo(action, props) {
        return buildActionInfo(action, props, { pushState });
    }

    /**
     * @param {BaseView} view
     * @param {ActWindowAction} action
     * @param {BaseView[]} views
     * @param {Object} props
     */
    function _getViewInfo(view, action, views, props = {}) {
        return buildViewInfo(view, action, views, props, {
            getView: _getView,
            switchView,
            doAction,
            pushState,
        });
    }

    /**
     * Computes the position of the controller in the nextStack according to options
     * @param {ActionOptions} options
     */
    function _computeStackIndex(options) {
        if (options.clearBreadcrumbs) {
            return 0;
        } else if (options.stackPosition === "replaceCurrentAction") {
            const currentController = controllerStack.at(-1);
            if (currentController) {
                return controllerStack.findIndex(
                    (ct) => ct.action.jsId === currentController.action.jsId,
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
                return controllerStack.findIndex((ct) => ct.action.jsId === last);
            }
            // TODO: throw if there is no previous action?
        } else if (options.index !== undefined) {
            return options.index;
        }
        return controllerStack.length;
    }

    /**
     * Open the action in a new window
     *
     * @param {ActionDescription} action
     * @param {Object} state
     */

    function _openActionInNewWindow(action, state) {
        // Session storage is duplicated in the new window
        // https://html.spec.whatwg.org/multipage/webstorage.html#webstorage
        // "After creating a new auxiliary browsing context and document, the session storage is copied over."

        // Store current action of the current window
        const currentAction = browser.sessionStorage.getItem("current_action");
        const currentState = browser.sessionStorage.getItem("current_state");
        // Store on the session the action for the new window
        browser.sessionStorage.setItem(
            "current_action",
            action._originalAction || "{}",
        );
        browser.sessionStorage.setItem("current_state", JSON.stringify(state));
        _openURL(router.stateToUrl(state));
        // restore the current action from the current window
        browser.sessionStorage.setItem("current_action", currentAction);
        browser.sessionStorage.setItem("current_state", currentState);
    }

    /**
     * Triggers a re-rendering with respect to the given controller.
     *
     * @private
     * @param {Controller} controller
     * @param {Object} [options]
     * @param {boolean} [options.clearBreadcrumbs]
     * @param {number} [options.index]
     * @param {any[]} [options.newStack]
     * @param {boolean} [options.newWindow]
     * @param {Function} [options.onClose]
     * @param {boolean} [options.noEmptyTransition]
     * @param {Function} [options.onActionReady]
     * @returns {Promise<any>}
     */
    async function _updateUI(controller, options = {}) {
        let resolve;
        let reject;
        let removeDialogFn;
        const currentActionProm = new Promise((_res, _rej) => {
            resolve = _res;
            reject = _rej;
        });
        const action = controller.action;
        if (action.target !== "new" && "newStack" in options) {
            controllerStack = options.newStack;
        }
        const index = _computeStackIndex(options);
        const nextStack = [...controllerStack.slice(0, index), controller];
        if (action.target !== "new" && options.newWindow) {
            return _openActionInNewWindow(action, makeActionState(nextStack));
        }
        // Compute breadcrumbs
        controller.config.breadcrumbs = reactive(
            action.target === "new" ? [] : _getBreadcrumbs(nextStack),
        );
        controller.config.getDisplayName = () => controller.displayName;
        controller.config.setDisplayName = (displayName) => {
            controller.displayName = displayName;
            if (controller === _getCurrentController()) {
                // if not mounted yet, will be done in "mounted"
                env.services.title.setParts({ action: controller.displayName });
            }
            if (action.target !== "new") {
                // This is a hack to force the reactivity when a new displayName is set
                controller.config.breadcrumbs.push(undefined);
                controller.config.breadcrumbs.pop();
            }
        };
        controller.config.setCurrentEmbeddedAction = (embeddedActionId) => {
            controller.currentEmbeddedActionId = embeddedActionId;
        };
        controller.config.setEmbeddedActions = (embeddedActions) => {
            controller.embeddedActions = embeddedActions;
        };
        controller.config.historyBack = () => {
            const previousController = controllerStack[controllerStack.length - 2];
            if (previousController) {
                restore(previousController.jsId);
            } else {
                env.bus.trigger("WEBCLIENT:LOAD_DEFAULT_APP");
            }
        };
        controller.config.isReloadingController = controller === controllerStack.at(-1);

        class ControllerComponent extends Component {
            static template = ControllerComponentTemplate;
            static Component = controller.Component;
            static props = {
                "*": true,
            };
            setup() {
                this.Component = controller.Component;
                this.titleService = useService("title");
                useDebugCategory("action", { action });
                useChildSubEnv({
                    config: controller.config,
                    pushStateBeforeReload: () => {
                        if (controller.isMounted) {
                            return;
                        }
                        pushState(nextStack);
                    },
                });
                if (action.target !== "new") {
                    this.__beforeLeave__ = new CallbackRecorder();
                    this.__getGlobalState__ = new CallbackRecorder();
                    this.__getLocalState__ = new CallbackRecorder();
                    useBus(env.bus, "CLEAR-UNCOMMITTED-CHANGES", (ev) => {
                        const callbacks = ev.detail;
                        const beforeLeaveFns = this.__beforeLeave__.callbacks;
                        callbacks.push(...beforeLeaveFns);
                    });
                    if (/** @type {any} */ (this.constructor).Component !== View) {
                        useChildSubEnv({
                            __beforeLeave__: this.__beforeLeave__,
                            __getGlobalState__: this.__getGlobalState__,
                            __getLocalState__: this.__getLocalState__,
                        });
                    }
                }

                onMounted(this.onMounted);
                onWillUnmount(this.onWillUnmount);
                onError(this.onError);
            }
            onError(error) {
                if (controller.isMounted) {
                    // the error occurred on the controller which is
                    // already in the DOM, so simply show the error
                    Promise.reject(error);
                    return;
                }
                if (!controller.isMounted && status(this) === "mounted") {
                    // The error occured during an onMounted hook of one of the components.
                    env.bus.trigger("ACTION_MANAGER:UPDATE", {
                        id: ++id,
                        Component: BlankComponent,
                        componentProps: {
                            onMounted: () => {},
                            withControlPanel: action.type === "ir.actions.act_window",
                        },
                    });
                    Promise.reject(error);
                    return;
                }
                // forward the error to the _updateUI caller then restore the action container
                // to an unbroken state
                reject(error);
                if (action.target === "new") {
                    removeDialogFn?.();
                    return;
                }
                const index = controllerStack.findIndex(
                    (ct) => ct.jsId === controller.jsId,
                );
                if (index > 0) {
                    // The error occurred while rendering an existing controller,
                    // so go back to the previous controller, of the current faulty one.
                    // This occurs when clicking on a breadcrumbs.
                    return restore(controllerStack[index - 1].jsId);
                }
                if (index === 0) {
                    // No previous controller to restore, so do nothing but display the error
                    return;
                }
                const lastController = controllerStack.at(-1);
                if (lastController) {
                    if (lastController.jsId !== controller.jsId) {
                        // the error occurred while rendering a new controller,
                        // so go back to the last non faulty controller
                        // (the error will be shown anyway as the promise
                        // has been rejected)
                        return restore(lastController.jsId);
                    }
                } else {
                    env.bus.trigger("ACTION_MANAGER:UPDATE", {});
                }
            }
            onMounted() {
                if (action.target === "new") {
                    dialog?.remove();
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

                    controllerStack = nextStack; // the controller is mounted, commit the new stack
                    pushState();
                    this.titleService.setParts({
                        action: controller.displayName,
                    });
                    browser.sessionStorage.setItem(
                        "current_action",
                        action._originalAction || "{}",
                    );
                    browser.sessionStorage.setItem("current_lang", user.lang);
                }
                resolve();
                env.bus.trigger(
                    "ACTION_MANAGER:UI-UPDATED",
                    getActionMode(action, actionRegistry),
                );
                controller.isMounted = true;
            }
            onWillUnmount() {
                controller.isMounted = false;
            }
            get componentProps() {
                const componentProps = { ...this.props };
                const updateActionState = componentProps.updateActionState;
                componentProps.updateActionState = (newState) =>
                    updateActionState(controller, newState);
                if (/** @type {any} */ (this.constructor).Component === View) {
                    componentProps.__beforeLeave__ = this.__beforeLeave__;
                    componentProps.__getGlobalState__ = this.__getGlobalState__;
                    componentProps.__getLocalState__ = this.__getLocalState__;
                }
                return componentProps;
            }
        }
        if (action.target === "new") {
            const actionDialogProps = {
                ActionComponent: ControllerComponent,
                actionProps: controller.props,
                actionType: action.type,
            };
            if (action.name) {
                actionDialogProps.title = action.name;
            }
            const size = DIALOG_SIZES[action.context.dialog_size];
            if (size) {
                actionDialogProps.size = size;
            }
            actionDialogProps.header =
                action.context.header ?? actionDialogProps.header;
            actionDialogProps.footer =
                action.context.footer ?? actionDialogProps.footer;
            const onClose = dialog?.onClose;
            delete dialog?.onClose;
            removeDialogFn = env.services.dialog.add(ActionDialog, actionDialogProps, {
                onClose: (closeParams) => _removeDialog(closeParams),
            });
            if (nextDialog) {
                nextDialog.remove();
            }
            nextDialog = {
                remove: removeDialogFn,
                onClose: onClose || options.onClose,
            };
            return currentActionProm;
        }

        const currentController = _getCurrentController();
        if (currentController?.getLocalState) {
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
        if (currentController?.getGlobalState) {
            const globalState = Object.assign(
                {},
                currentController.action.globalState,
                currentController.getGlobalState(), // what if this = {}?
            );

            currentController.action.globalState = globalState;
            // Avoid pushing the globalState, if the state on the router was changed.
            // For instance, if a link was clicked, the state of the router will be the one of the link and not the one of the currentController.
            // Or when using the back or forward buttons on the browser.
            if (
                currentController.state.action === router.current.action &&
                currentController.state.active_id === router.current.active_id &&
                currentController.state.resId === router.current.resId
            ) {
                router.pushState({ globalState }, { sync: true });
            }
        }
        if (controller.action.globalState) {
            controller.props.globalState = controller.action.globalState;
        }

        if (options.clearBreadcrumbs && !options.noEmptyTransition) {
            const def = new Deferred();
            const isActWindow = action.type === "ir.actions.act_window";
            env.bus.trigger("ACTION_MANAGER:UPDATE", {
                id: ++id,
                Component: SkeletonView,
                componentProps: {
                    onMounted: () => def.resolve(),
                    viewType: isActWindow ? controller.props.type : undefined,
                    withControlPanel: isActWindow,
                },
            });
            await def;
        }
        if (options.onActionReady) {
            options.onActionReady(action);
        }
        controller.__info__ = {
            id: ++id,
            Component: ControllerComponent,
            componentProps: controller.props,
        };
        env.services.dialog.closeAll({ noReload: true });
        env.bus.trigger("ACTION_MANAGER:UPDATE", controller.__info__);
        await currentActionProm;
    }

    // ---------------------------------------------------------------------------
    // ir.actions.act_url
    // ---------------------------------------------------------------------------

    function _openURL(url) {
        const w = browser.open(url, "_blank");
        if (!w || w.closed || typeof w.closed === "undefined") {
            const msg = _t(
                "A popup window has been blocked. You may need to change your " +
                    "browser settings to allow popup windows for this page.",
            );
            env.services.notification.add(msg, {
                sticky: true,
                type: "warning",
            });
        }
    }

    /**
     * Executes actions of type 'ir.actions.act_url', i.e. redirects to the
     * given url.
     *
     * @private
     * @param {ActURLAction} action
     * @param {ActionOptions} options
     */
    function _executeActURLAction(action, options) {
        let url = action.url;
        if (url && !(url.startsWith("http") || url.startsWith("/"))) {
            url = "/" + url;
        }
        if (action.target === "self") {
            browser.location.assign(url);
        } else if (action.target === "download") {
            _openURL(url);
        } else {
            _openURL(url);
            if (action.close) {
                return doAction(
                    { type: "ir.actions.act_window_close" },
                    { onClose: options.onClose },
                );
            } else if (options.onClose) {
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
    async function _executeActWindowAction(action, options) {
        if (action.target !== "new" && !options.newWindow) {
            const canProceed = await clearUncommittedChanges(
                env,
                pick(options, "forceLeave"),
            );
            if (!canProceed) {
                return;
            }
        }
        const views = buildActionViews(action);

        let view =
            (options.viewType && views.find((v) => v.type === options.viewType)) ||
            views[0];
        if (env.isSmall) {
            view = findView(views, view.multiRecord, action.mobile_view_mode) || view;
        }

        const controller = _makeController({
            Component: View,
            action,
            view,
            views,
            ..._getViewInfo(view, action, views, options.props),
        });
        action.controllers[view.type] = controller;

        const newStackLastController = options.newStack?.at(-1);
        if (newStackLastController?.lazy) {
            const multiView = action.views.find(
                (view) => view[1] !== "form" && view[1] !== "search",
            );
            if (multiView) {
                // If the current action has a multi-record view, we add the last
                // controller to the breadcrumb controllers.
                delete newStackLastController.lazy;
                newStackLastController.displayName =
                    action.display_name || action.name || "";
                newStackLastController.action = action;
                newStackLastController.props.type = multiView[1];
            } else {
                // If the current action doesn't have a multi-record view,
                // we don't need to add the last controller to the breadcrumb controllers
                options.newStack.splice(-1);
            }
        }
        return _updateUI(controller, options);
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
        action.path ||= clientAction.path;
        if (clientAction.prototype instanceof Component) {
            if (action.target !== "new" && !options.newWindow) {
                const canProceed = await clearUncommittedChanges(
                    env,
                    pick(options, "forceLeave"),
                );
                if (!canProceed) {
                    return;
                }
                if (clientAction.target) {
                    action.target = clientAction.target;
                }
            }
            const props =
                /** @type {any} */ (clientAction).extractProps?.(action) || {};
            const controller = _makeController({
                Component: /** @type {any} */ (clientAction),
                action,
                ..._getActionInfo(action, { ...props, ...options.props }),
            });
            controller.displayName ||= clientAction.displayName?.toString() || "";
            return _updateUI(controller, options);
        } else {
            const next = await /** @type {any} */ (clientAction)(env, action, options);
            if (next) {
                return doAction(next, options);
            }
        }
    }

    // ---------------------------------------------------------------------------
    // ir.actions.report
    // ---------------------------------------------------------------------------

    /** Report executor context shared with reports/report_executor.js. */
    const reportCtx = {
        get env() {
            return env;
        },
        doAction,
        makeController: _makeController,
        getActionInfo: _getActionInfo,
        updateUI: _updateUI,
    };

    function _executeReportAction(action, options) {
        return executeReportAction(action, options, reportCtx);
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
        const runProm = rpc("/web/action/run", {
            action_id: action.id,
            context: makeContext([user.context, action.context]),
        });
        let nextAction = await keepLast.add(runProm);
        nextAction = nextAction || { type: "ir.actions.act_window_close" };
        if (nextAction.help) {
            nextAction.help = markup(nextAction.help);
        }
        if (typeof nextAction === "object") {
            nextAction.path ||= action.path;
        }
        return /** @type {any} */ (doAction(nextAction, options));
    }

    function _executeCloseAction(action = {}, options = {}) {
        if (dialog) {
            return _removeDialog(action.infos);
        }
        return options.onClose?.(action.infos);
    }

    /** @type {Record<string, (action: Object, options: ActionOptions) => Promise>} */
    const actionExecutors = {
        "ir.actions.act_url": _executeActURLAction,
        "ir.actions.act_window": _executeActWindowAction,
        "ir.actions.act_window_close": _executeCloseAction,
        "ir.actions.client": _executeClientAction,
        "ir.actions.server": _executeServerAction,
        "ir.actions.report": _executeReportAction,
    };

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

        if (Object.hasOwn(actionExecutors, action.type)) {
            return actionExecutors[action.type](action, options);
        }
        const handler = actionHandlersRegistry.get(action.type, null);
        if (handler !== null) {
            return handler({ env, action, options });
        }
        throw new Error(
            `The ActionManager service can't handle actions of type ${action.type}`,
        );
    }

    /** Context shared with extracted action_button_executor module. */
    const buttonCtx = {
        env,
        keepLast,
        loadAction: _loadAction,
        doAction,
        get doActionButton() {
            return doActionButton;
        },
        executeCloseAction: _executeCloseAction,
    };

    /**
     * Executes an action on top of the current one (typically, when a button in a
     * view is clicked). Delegates to the extracted executeActionButton.
     *
     * @param {DoActionButtonParams} params
     * @param {Object} [options={}]
     * @returns {Promise<void>}
     */
    async function doActionButton(params, options) {
        return executeActionButton(params, options, buttonCtx);
    }

    /**
     * Switches to the given view type in action of the last controller of the
     * stack. This action must be of type 'ir.actions.act_window'.
     *
     * @param {ViewType} viewType
     * @param {Object} [props={}]
     * @params {Object} [options={}]
     * @params {boolean} [options.newWindow] set to true to open the action in a new tab/window.
     * @throws {ViewNotFoundError} if the viewType is not found on the current action
     * @returns {Promise<Number>}
     */
    async function switchView(
        viewType,
        props = {},
        { newWindow } = /** @type {any} */ ({}),
    ) {
        await keepLast.add(Promise.resolve());
        if (dialog) {
            // we don't want to switch view when there's a dialog open, as we would
            // not switch in the correct action (action in background != dialog action)
            return;
        }
        const controller = controllerStack.at(-1);
        const view = _getView(viewType);
        if (!view) {
            throw new ViewNotFoundError(
                _t(
                    "No view of type '%s' could be found in the current action.",
                    viewType,
                ),
            );
        }
        const newController =
            controller.action.controllers[viewType] ||
            _makeController({
                Component: View,
                action: controller.action,
                views: controller.views,
                view,
            });

        if (!newWindow) {
            const canProceed = await clearUncommittedChanges(env);
            if (!canProceed) {
                return;
            }
        }

        Object.assign(
            newController,
            _getViewInfo(view, controller.action, controller.views, props),
        );
        controller.action.controllers[viewType] = newController;
        let index;
        if (view.multiRecord) {
            index = controllerStack.findIndex(
                (ct) => ct.action.jsId === controller.action.jsId,
            );
            index = index > -1 ? index : controllerStack.length - 1;
        } else {
            // This case would mostly happen when loadState detects a change in the URL.
            // Also, I guess we may need it when we have other monoRecord views
            index = controllerStack.findIndex(
                (ct) =>
                    ct.action.jsId === controller.action.jsId && !ct.view.multiRecord,
            );
            index = index > -1 ? index : controllerStack.length;
        }
        return _updateUI(newController, { newWindow, index });
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
            const msg = jsId
                ? "Invalid controller to restore"
                : "No controller to restore";
            throw new ControllerNotFoundError(msg);
        }
        const canProceed = await clearUncommittedChanges(env);
        if (!canProceed) {
            return;
        }
        const controller = controllerStack[index];
        if (controller.virtual) {
            const actionParams = _getActionParams(controller.state);
            if (!actionParams) {
                throw new Error(
                    "Attempted to restore a virtual controller whose state is invalid",
                );
            }
            const { actionRequest, options } = actionParams;
            controllerStack = controllerStack.slice(0, index);
            return doAction(actionRequest, options);
        }
        if (controller.action.type === "ir.actions.act_window") {
            if (controller.isMounted) {
                controller.exportedState = controller.getLocalState();
            }
            const { action, exportedState, view, views } = controller;
            const props = { ...controller.props };
            if (exportedState && "resId" in exportedState) {
                // When restoring, we want to use the last exported ID of the controller
                props.resId = exportedState.resId;
            }
            Object.assign(controller, _getViewInfo(view, action, views, props));
        }
        return _updateUI(controller, { index });
    }

    /**
     * Restores a stack of virtual controllers from the current contents of the
     * state (usually router.current) and performs a "doAction" on the last one.
     *
     * @private
     * @param {object} [state]
     * @returns {Promise<boolean>} true if doAction was performed
     */

    async function loadState(state = router.current) {
        const lang = browser.sessionStorage.getItem("current_lang");
        if (lang && lang !== user.lang) {
            browser.sessionStorage.removeItem("current_action");
            browser.sessionStorage.removeItem("current_lang");
            browser.sessionStorage.removeItem("current_state");
        }
        const newStack = await _controllersFromState(state);
        const actionParams = _getActionParams(state);
        if (actionParams) {
            // Params valid => performs a "doAction"
            const { actionRequest, options } = actionParams;
            if (options.index) {
                options.newStack = newStack.slice(0, options.index);
                delete options.index;
            } else {
                options.newStack = newStack;
            }
            try {
                await doAction(actionRequest, options);
            } catch (error) {
                if (
                    error.exceptionName ===
                    "odoo.addons.web.controllers.action.MissingActionError"
                ) {
                    if (state.actionStack.length > 1) {
                        const newState = {
                            ...state.actionStack.slice(0, -1).at(-1),
                            actionStack: [...state.actionStack.slice(0, -1)],
                        };
                        return loadState(newState);
                    } else {
                        env.bus.trigger("WEBCLIENT:LOAD_DEFAULT_APP");
                    }
                } else {
                    throw error;
                }
            }
            return true;
        }
    }

    function pushState(cStack = controllerStack) {
        if (!cStack.length) {
            return;
        }

        const newState = makeActionState(cStack);
        browser.sessionStorage.setItem("current_state", JSON.stringify(newState));

        cStack.at(-1).state = newState;
        router.pushState(newState, { replace: true });
    }
    return {
        doAction,
        doActionButton,
        switchView,
        restore,
        loadState,
        async loadAction(actionRequest, context) {
            const action = await _loadAction(actionRequest, context);
            return _preprocessAction(action, context);
        },
        get currentController() {
            return _getCurrentController();
        },
        get currentAction() {
            return _getCurrentAction();
        },
    };
}

export const actionService = {
    dependencies: ["dialog", "effect", "localization", "notification", "title", "ui"],
    start(env) {
        return makeActionManager(env);
    },
};

registry.category("services").add("action", actionService);
