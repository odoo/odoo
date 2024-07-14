/** @odoo-module **/
import { registry } from "@web/core/registry";
import { resetViewCompilerCache } from "@web/views/view_compiler";
import { _t } from "@web/core/l10n/translation";

import { EventBus, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const URL_VIEW_KEY = "_view_type";
const URL_ACTION_KEY = "_action";
const URL_TAB_KEY = "_tab";
const URL_MODE_KEY = "mode";
const URL_REPORT_ID_KEY = "_report_id";

export const MODES = {
    EDITOR: "editor",
    HOME_MENU: "home_menu",
    APP_CREATOR: "app_creator",
};

export class NotEditableActionError extends Error {}

const SUPPORTED_VIEW_TYPES = {
    activity: _t("Activity"),
    calendar: _t("Calendar"),
    cohort: _t("Cohort"),
    form: _t("Form"),
    gantt: _t("Gantt"),
    graph: _t("Graph"),
    kanban: _t("Kanban"),
    list: _t("List"),
    map: _t("Map"),
    pivot: _t("Pivot"),
    search: _t("Search"),
};

export function viewTypeToString(vType) {
    return SUPPORTED_VIEW_TYPES[vType] || vType;
}

export const studioService = {
    dependencies: ["action", "color_scheme", "home_menu", "router", "rpc", "menu", "notification"],
    async start(env, { color_scheme, rpc, menu, notification }) {
        const supportedViewTypes = Object.keys(SUPPORTED_VIEW_TYPES);

        function _getCurrentAction() {
            const currentController = env.services.action.currentController;
            return currentController ? currentController.action : null;
        }

        function _isStudioEditable(action) {
            if (action.type === "ir.actions.client") {
                // home_menu is somehow customizable (app creator)
                return action.tag === "menu" ? true : false;
            }
            if (action.type === "ir.actions.act_window" && action.xml_id) {
                if (
                    action.res_model.indexOf("settings") > -1 &&
                    action.res_model.indexOf("x_") !== 0
                ) {
                    return false; // settings views aren't editable; but x_settings is
                }
                if (action.res_model === "board.board") {
                    return false; // dashboard isn't editable
                }
                if (action.view_mode === "qweb") {
                    // Apparently there is a QWebView that allows to
                    // implement ActWindow actions that are completely custom
                    // but not editable by studio
                    return false;
                }
                if (action.res_model === "knowledge.article") {
                    // The knowledge form view is very specific and custom, it doesn't make sense
                    // to edit it. Editing the list and kanban is more debatable, but for simplicity's sake
                    // we set them to not editable too.
                    return false;
                }
                if (action.view_id && action.view_id[1] === "res.users.preferences.form.inherit") {
                    // The employee profile view is too complex to handle inside studio.
                    // @see SELF_READABLE_FIELDS.
                    return false;
                }
                return action.res_model ? true : false;
            }
            return false;
        }

        function isViewEditable(view) {
            return view && supportedViewTypes.includes(view);
        }

        const bus = new EventBus();
        let inStudio = false;

        const menuSelectMenu = menu.selectMenu;
        menu.selectMenu = async (argMenu) => {
            if (!inStudio) {
                return menuSelectMenu.call(menu, argMenu);
            } else {
                try {
                    argMenu = typeof argMenu === "number" ? menu.getMenu(argMenu) : argMenu;
                    await open(MODES.EDITOR, argMenu.actionID);
                    menu.setCurrentMenu(argMenu);
                } catch (e) {
                    if (e instanceof NotEditableActionError) {
                        notification.add(_t("This action is not editable by Studio"), {
                            type: "danger",
                        });
                        return;
                    }
                    throw e;
                }
            }
        };

        const state = {
            studioMode: null,
            editedViewType: null,
            editedAction: null,
            editedControllerState: null,
            editorTab: "views",
            editedReport: null,
        };

        async function _loadParamsFromURL() {
            const currentHash = env.services.router.current.hash;
            if (currentHash.action === "studio") {
                state.studioMode = currentHash[URL_MODE_KEY];
                state.editedViewType = currentHash[URL_VIEW_KEY] || null;
                const editorTab = currentHash[URL_TAB_KEY] || null;
                state.editorTab = editorTab;
                if (editorTab === "reports") {
                    const reportId = currentHash[URL_REPORT_ID_KEY] || null;
                    if (reportId) {
                        state.editedReport = { res_id: reportId };
                    }
                }

                const editedActionId = currentHash[URL_ACTION_KEY];
                const additionalContext = {};
                if (state.studioMode === MODES.EDITOR) {
                    if (currentHash.active_id) {
                        additionalContext.active_id = currentHash.active_id;
                    }
                    if (editedActionId) {
                        state.editedAction = await env.services.action.loadAction(
                            editedActionId,
                            additionalContext
                        );
                    } else {
                        state.editedAction = null;
                    }
                }
                if (!state.editedAction || !_isStudioEditable(state.editedAction)) {
                    state.studioMode = state.studioMode || MODES.HOME_MENU;
                    state.editedAction = null;
                    state.editedViewType = null;
                    state.editorTab = null;
                }
            }
        }

        let studioProm = _loadParamsFromURL();
        env.bus.addEventListener("ROUTE_CHANGE", async () => {
            studioProm = _loadParamsFromURL();
        });

        async function _openStudio(targetMode, action = false, viewType = false) {
            if (!targetMode) {
                throw new Error("mode is mandatory");
            }

            const previousState = { ...state };
            const options = {};
            if (targetMode === MODES.EDITOR) {
                let controllerState;
                if (!action) {
                    // systray open
                    const currentController = env.services.action.currentController;
                    if (currentController) {
                        action = currentController.action;
                        viewType = currentController.view.type;
                        controllerState = Object.assign({}, currentController.getLocalState());
                        const { resIds } = currentController.getGlobalState() || {};
                        controllerState.resIds = resIds || [controllerState.resId];
                    }
                }
                if (!_isStudioEditable(action)) {
                    throw new NotEditableActionError();
                }
                if (action !== state.editedAction) {
                    options.clearBreadcrumbs = true;
                    options.noEmptyTransition = true;
                }
                state.editedAction = action;
                const vtype = viewType || action.views[0][1]; // fallback on first view of action
                state.editedViewType = isViewEditable(vtype) ? vtype : null;
                state.editorTab = "views";
                state.editedControllerState = controllerState || {};
            }
            if (inStudio) {
                options.stackPosition = "replaceCurrentAction";
            }
            state.studioMode = targetMode;

            let res;
            try {
                res = await env.services.action.doAction("studio", options);
            } catch (e) {
                Object.assign(state, previousState);
                throw e;
            }
            // force color_scheme light
            if (color_scheme.activeColorScheme === "dark") {
                // ensure studio is fully loaded
                await new Promise((resolve) => setTimeout(resolve));
                color_scheme.applyColorScheme();
            }
            return res;
        }

        async function open(mode = false, actionId = false) {
            if (!mode && inStudio) {
                throw new Error("can't already be in studio");
            }
            if (!mode) {
                mode = env.services.home_menu.hasHomeMenu ? MODES.HOME_MENU : MODES.EDITOR;
            }
            let action;
            if (actionId) {
                action = await env.services.action.loadAction(actionId);
            }
            resetViewCompilerCache();
            return _openStudio(mode, action);
        }

        async function leave() {
            if (!inStudio) {
                throw new Error("leave when not in studio???");
            }
            env.bus.trigger("CLEAR-CACHES");

            const options = {
                onActionReady: () => resetViewCompilerCache(),
                stackPosition: "replacePreviousAction", // If target is menu, then replaceCurrent, see comment above why we cannot do this
            };
            let actionId;
            if (state.studioMode === MODES.EDITOR) {
                actionId = state.editedAction.id;
                options.additionalContext = state.editedAction.context;
                options.viewType = state.editedViewType;
                if (state.editedControllerState) {
                    options.props = { resId: state.editedControllerState.resId };
                }
            } else {
                actionId = "menu";
            }
            await env.services.action.doAction(actionId, options);
            // force rendering of the main navbar to allow adaptation of the size
            env.bus.trigger("MENUS:APP-CHANGED");
            // reset color_scheme
            if (color_scheme.activeColorScheme === "dark") {
                // ensure studio is fully unloaded
                await new Promise((resolve) => setTimeout(resolve));
                color_scheme.applyColorScheme();
            }
            state.studioMode = null;
        }

        async function reload(params = {}, reset = true) {
            resetViewCompilerCache();
            env.bus.trigger("CLEAR-CACHES");
            const actionContext = state.editedAction.context;
            let additionalContext;
            if (actionContext.active_id) {
                additionalContext = { active_id: actionContext.active_id };
            }
            if (actionContext.active_ids) {
                additionalContext = Object.assign(additionalContext || {}, {
                    active_ids: actionContext.active_ids,
                });
            }
            const action = await env.services.action.loadAction(
                state.editedAction.id,
                additionalContext
            );
            setParams({ action, ...params }, reset);
        }

        function toggleHomeMenu() {
            if (!inStudio) {
                throw new Error("is it possible?");
            }
            let targetMode;
            if (state.studioMode === MODES.APP_CREATOR || state.studioMode === MODES.EDITOR) {
                targetMode = MODES.HOME_MENU;
            } else {
                targetMode = MODES.EDITOR;
            }
            const action = targetMode === MODES.EDITOR ? state.editedAction : null;
            if (targetMode === MODES.EDITOR && !action) {
                throw new Error("this button should not be clickable/visible");
            }
            const viewType = targetMode === MODES.EDITOR ? state.editedViewType : null;
            return _openStudio(targetMode, action, viewType);
        }

        function pushState() {
            const hash = { action: "studio" };
            hash[URL_MODE_KEY] = state.studioMode;
            hash[URL_ACTION_KEY] = undefined;
            hash[URL_VIEW_KEY] = undefined;
            hash[URL_TAB_KEY] = undefined;
            if (state.studioMode === MODES.EDITOR) {
                hash[URL_ACTION_KEY] = JSON.stringify(state.editedAction.id);
                hash[URL_VIEW_KEY] = state.editedViewType || undefined;
                hash[URL_TAB_KEY] = state.editorTab;
            }
            if (
                state.editedAction &&
                state.editedAction.context &&
                state.editedAction.context.active_id
            ) {
                hash.active_id = state.editedAction.context.active_id;
            }

            if (state.editorTab === "reports" && state.editedReport) {
                hash[URL_REPORT_ID_KEY] = state.editedReport.res_id;
            }
            env.services.router.pushState(hash, { replace: true });
        }

        function setParams(params = {}, reset = true) {
            if ("mode" in params) {
                state.studioMode = params.mode;
            }
            if ("viewType" in params) {
                state.editedViewType = params.viewType || null;
            }
            if ("action" in params) {
                if ((state.editedAction && state.editedAction.id) !== params.action.id) {
                    state.editedControllerState = null;
                }
                state.editedAction = params.action || null;
            }
            if ("editorTab" in params) {
                state.editorTab = params.editorTab;
                if (!("viewType" in params)) {
                    // clean me
                    state.editedViewType = null;
                }
                if (!("editedReport" in params)) {
                    state.editedReport = null;
                }
            }
            if ("editedReport" in params) {
                state.editedReport = params.editedReport;
            }
            if ("controllerState" in params) {
                state.editedControllerState = params.controllerState;
            }
            if (state.editorTab !== "reports") {
                state.editedReport = null;
            }
            bus.trigger("UPDATE", { reset });
        }

        env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", (ev) => {
            const mode = ev.detail;
            if (mode === "new") {
                return;
            }
            const action = _getCurrentAction();
            inStudio = action.tag === "studio";
        });

        const isAllowedCache = {
            activity: {},
            chatter: {},
        };

        function isAllowed(type, resModel) {
            if (!Object.keys(isAllowedCache).includes(type)) {
                return;
            }
            let val;
            if (resModel in isAllowedCache[type]) {
                val = isAllowedCache[type][resModel];
            } else {
                val = rpc(`/web_studio/${type}_allowed`, { model: resModel });
                isAllowedCache[type][resModel] = val;
            }
            return val;
        }

        return {
            MODES,
            bus,
            isStudioEditable() {
                const action = _getCurrentAction();
                return action ? _isStudioEditable(action) : false;
            },
            open,
            reload,
            pushState,
            leave,
            toggleHomeMenu,
            setParams,
            get ready() {
                return studioProm;
            },
            get mode() {
                return state.studioMode;
            },
            get editedAction() {
                return state.editedAction;
            },
            get editedViewType() {
                return state.editedViewType;
            },
            get editedControllerState() {
                return state.editedControllerState;
            },
            get editedReport() {
                return state.editedReport;
            },
            get editorTab() {
                return state.editorTab;
            },
            isAllowed,
        };
    },
};

registry.category("services").add("studio", studioService);

export function useStudioServiceAsReactive() {
    const studio = useService("studio");
    const state = useState({ ...studio });
    state.requestId = 1;

    function onUpdate({ detail }) {
        Object.assign(state, studio);
        if (detail.reset) {
            state.requestId++;
        }
    }
    studio.bus.addEventListener("UPDATE", onUpdate);
    onWillUnmount(() => studio.bus.removeEventListener("UPDATE", onUpdate));
    return state;
}
