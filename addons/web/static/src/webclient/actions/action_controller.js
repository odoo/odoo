/** @odoo-module **/

import { useBus } from "@web/core/bus_hook";
import { cleanDomFromBootstrap } from "@web/legacy/utils";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

const { Component, hooks, tags } = owl;
const actionRegistry = registry.category("actions");

let dialogCloseResolve;

export class ActionController extends Component {
    setup() {
        this.Component = this.props.controller.Component;
        this.action = this.props.controller.action;
        this.componentRef = hooks.useRef("component");
        this.registerCallback = null;
        if (this.action.target !== "new") {
            let beforeLeaveFn;
            this.registerCallback = (type, fn) => {
                switch (type) {
                    case "export":
                        this.props.controller.getState = fn;
                        break;
                    case "beforeLeave":
                        beforeLeaveFn = fn;
                        break;
                }
            };
            useBus(this.env.bus, "CLEAR-UNCOMMITTED-CHANGES", (callbacks) => {
                if (beforeLeaveFn) {
                    callbacks.push(beforeLeaveFn);
                }
            });
        }
    }
    catchError(error) {
        this.props.reject(error);
        cleanDomFromBootstrap();
        if (this.action.target === "new") {
            // get the dialog service to close the dialog.
            throw error;
        } else {
            const lastCt = this.props.controllerStack[this.props.controllerStack.length - 1];
            const info = lastCt ? lastCt.__info__ : {};
            this.env.bus.trigger("ACTION_MANAGER:UPDATE", info);
        }
    }
    mounted() {
        if (this.action.target === "new") {
            this.props.dialogCloseProm = new Promise((_r) => {
                dialogCloseResolve = _r;
            }).then(() => {
                this.props.dialogCloseProm = undefined;
            });
            for (const key in this.props.dialog) delete this.props.dialog[key];
            for (const key in this.props.nextDialog) {
                this.props.dialog[key] = this.props.nextDialog[key];
            }
        } else {
            // LEGACY CODE COMPATIBILITY: remove when controllers will be written in owl
            // we determine here which actions no longer occur in the nextStack,
            // and we manually destroy all their controller's widgets
            const nextStackActionIds = this.props.nextStack.map((c) => c.action.jsId);
            const toDestroy = new Set();
            for (const c of this.props.controllerStack) {
                if (!nextStackActionIds.includes(c.action.jsId)) {
                    if (c.action.type === "ir.actions.act_window") {
                        for (const viewType in c.action.controllers) {
                            toDestroy.add(c.action.controllers[viewType]);
                        }
                    } else {
                        toDestroy.add(c);
                    }
                }
            }
            for (const c of toDestroy) {
                if (c.exportedState) {
                    c.exportedState.__legacy_widget__.destroy();
                }
            }
            // END LEGACY CODE COMPATIBILITY
            this.props.controllerStack.length = 0;
            if (this.props.nextStack) {
                this.props.controllerStack.push(...this.props.nextStack);
            }
            // wait Promise callbacks to be executed
            this._pushState(this.props.controller);
            browser.sessionStorage.setItem("current_action", this.action._originalAction);
        }
        this.props.resolve();
        this.env.bus.trigger("ACTION_MANAGER:UI-UPDATED", this._getActionMode(this.action));
    }
    willUnmount() {
        if (this.action.target === "new" && dialogCloseResolve) {
            dialogCloseResolve();
        }
    }
    onHistoryBack() {
        const previousController = this.props.controllerStack[
            this.props.controllerStack.length - 2
        ];
        if (previousController && !this.props.dialogCloseProm) {
            this.props.restore(previousController.jsId);
        } else {
            this.props.executeCloseAction();
        }
    }
    onTitleUpdated(ev) {
        this.props.controller.title = ev.detail;
    }
    _pushState(controller) {
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
                newState.active_id = `${activeId}`;
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
            newState.id = props.resId ? `${props.resId}` : undefined;
        }
        this.env.services.router.pushState(newState, { replace: true });
    }
    /**
     * @param {Action} action
     * @returns {ActionMode}
     */
    _getActionMode(action) {
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
        if (this.props.controllerStack.some((c) => c.action.target === "fullscreen")) {
            // Force fullscreen when one of the controllers is set to fullscreen
            return "fullscreen";
        }
        // Default: current
        return "current";
    }
}
ActionController.template = tags.xml`<t t-component="Component" t-props="props"
                                            registerCallback="registerCallback"
                                            t-ref="component"
                                            t-on-history-back="onHistoryBack"
                                            t-on-controller-title-updated.stop="onTitleUpdated"/>`;
