/** @odoo-module **/

import Context from "web.Context";
import core from "web.core";
import { ComponentAdapter } from "web.OwlCompatibility";
import { objectToQuery } from "../core/browser/router_service";
import { useDebugCategory } from "../core/debug/debug_context";
import { Dialog } from "../core/dialog/dialog";
import { useEffect, useService } from "@web/core/utils/hooks";
import { ViewNotFoundError } from "../webclient/actions/action_service";
import { cleanDomFromBootstrap, wrapSuccessOrFail } from "./utils";
import { mapDoActionOptionAPI } from "./backend_utils";

const { Component, tags, hooks } = owl;

const warningDialogBodyTemplate = tags.xml`<p style="white-space:pre-wrap" t-esc="props.message"/>`;

class ActionAdapter extends ComponentAdapter {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.router = useService("router");
        this.title = useService("title");
        this.notifications = useService("notification");
        this.dialogs = useService("dialog");
        this.wowlEnv = this.env;
        // a legacy widget widget can push_state anytime including during its async rendering
        // In Wowl, we want to have all states pushed during the same setTimeout.
        // This is protected in legacy (backward compatibility) but should not e supported in Wowl
        this.tempQuery = {};
        let originalUpdateControlPanel;
        useEffect(
            () => {
                const query = this.widget.getState();
                Object.assign(query, this.tempQuery);
                this.tempQuery = null;
                this.__widget = this.widget;
                if (!this.wowlEnv.inDialog) {
                    this.pushState(query);
                }
                this.wowlEnv.bus.on("ACTION_MANAGER:UPDATE", this, () => {
                    this.env.bus.trigger("close_dialogs");
                    cleanDomFromBootstrap();
                });
                originalUpdateControlPanel = this.__widget.updateControlPanel.bind(this.__widget);
                this.__widget.updateControlPanel = (newProps) => {
                    this.trigger("controller-title-updated", this.__widget.getTitle());
                    return originalUpdateControlPanel(newProps);
                };
                core.bus.trigger("DOM_updated");

                return () => {
                    this.__widget.updateControlPanel = originalUpdateControlPanel;
                    this.wowlEnv.bus.off("ACTION_MANAGER:UPDATE", this);
                };
            },
            () => []
        );
        hooks.useExternalListener(window, "click", () => {
            cleanDomFromBootstrap();
        });
    }

    get actionId() {
        throw new Error("Should be implement by specific adapters");
    }

    pushState(state) {
        if (this.wowlEnv.inDialog) {
            return;
        }
        const query = objectToQuery(state);
        if (this.tempQuery) {
            Object.assign(this.tempQuery, query);
            return;
        }
        if (this.widget) {
            const actionTitle = this.widget.getTitle();
            if (actionTitle) {
                this.trigger("controller-title-updated", actionTitle);
            }
        }
        this.router.pushState(query);
    }

    _trigger_up(ev) {
        const payload = ev.data;
        if (ev.name === "do_action") {
            if (payload.action.context) {
                payload.action.context = new Context(payload.action.context).eval();
            }
            this.onReverseBreadcrumb = payload.options && payload.options.on_reverse_breadcrumb;
            const legacyOptions = mapDoActionOptionAPI(payload.options);
            wrapSuccessOrFail(this.actionService.doAction(payload.action, legacyOptions), payload);
        } else if (ev.name === "breadcrumb_clicked") {
            this.actionService.restore(payload.controllerID);
        } else if (ev.name === "push_state") {
            this.pushState(payload.state);
        } else if (ev.name === "set_title_part") {
            const { part, title } = payload;
            this.title.setParts({ [part]: title || null });
        } else if (ev.name === "warning") {
            if (payload.type === "dialog") {
                class WarningDialog extends Dialog {
                    setup() {
                        super.setup();
                        this.title = this.props.title;
                    }
                }
                WarningDialog.bodyTemplate = warningDialogBodyTemplate;
                this.dialogs.add(WarningDialog, {
                    title: payload.title,
                    message: payload.message,
                });
            } else {
                this.notifications.add(payload.message, {
                    className: payload.className,
                    sticky: payload.sticky,
                    title: payload.title,
                    type: "warning",
                });
            }
        } else {
            super._trigger_up(ev);
        }
    }

    /**
     * This function is called just before the component will be unmounted,
     * because it will be replaced by another one. However, we need to keep it
     * alive, because we might come back to this one later. We thus return the
     * widget instance, and set this.widget to null so that it is not destroyed
     * by the compatibility layer. That instance will be destroyed by the
     * ActionManager service when it will be removed from the controller stack,
     * and if we ever come back to that controller, the instance will be given
     * in props so that we can re-use it.
     */
    exportState() {
        this.widget = null;
        return {
            __legacy_widget__: this.__widget,
            __on_reverse_breadcrumb__: this.onReverseBreadcrumb,
        };
    }

    canBeRemoved() {
        return this.__widget.canBeRemoved();
    }

    /**
     * @override
     */
    willUnmount() {
        if (this.__widget && this.__widget.on_detach_callback) {
            this.__widget.on_detach_callback();
        }
        super.willUnmount();
    }
    __destroy() {
        if (this.actionService.__legacy__isActionInStack(this.actionId)) {
            this.widget = null;
        }
        super.__destroy(...arguments);
    }
}

export class ClientActionAdapter extends ActionAdapter {
    setup() {
        super.setup();
        useDebugCategory("action", { action: this.props.widgetArgs[0] });
        owl.hooks.onMounted(() => {
            const action = this.props.widgetArgs[0];
            if ("params" in action) {
                const newState = {};
                Object.entries(action.params).forEach(([k, v]) => {
                    if (typeof v === "string" || typeof v === "number") {
                        newState[k] = v;
                    }
                });
                this.wowlEnv.services.router.pushState(newState);
            }
        });
        this.env = Component.env;
    }

    get actionId() {
        return this.props.widgetArgs[0].jsId;
    }

    async willStart() {
        if (this.props.widget) {
            this.widget = this.props.widget;
            this.widget.setParent(this);
            if (this.props.onReverseBreadcrumb) {
                await this.props.onReverseBreadcrumb();
            }
            return this.updateWidget();
        }
        return super.willStart();
    }

    /**
     * @override
     */
    updateWidget() {
        return this.widget.do_show();
    }

    do_push_state(state) {
        this.pushState(state);
    }
}

const magicReloadSymbol = Symbol("magicReload");

function useMagicLegacyReload() {
    const comp = Component.current;
    if (comp.props.widget && comp.props.widget[magicReloadSymbol]) {
        return comp.props.widget[magicReloadSymbol];
    }
    let legacyReloadProm = null;
    const getReloadProm = () => legacyReloadProm;
    let manualReload;
    useEffect(
        () => {
            const widget = comp.widget;
            const controllerReload = widget.reload;
            widget.reload = function (...args) {
                manualReload = true;
                legacyReloadProm = controllerReload.call(widget, ...args);
                return legacyReloadProm.finally(() => {
                    if (manualReload) {
                        legacyReloadProm = null;
                        manualReload = false;
                    }
                });
            };
            const controllerUpdate = widget.update;
            widget.update = function (...args) {
                const updateProm = controllerUpdate.call(widget, ...args);
                const manualUpdate = !manualReload;
                if (manualUpdate) {
                    legacyReloadProm = updateProm;
                }
                return updateProm.finally(() => {
                    if (manualUpdate) {
                        legacyReloadProm = null;
                    }
                });
            };
            widget[magicReloadSymbol] = getReloadProm;
        },
        () => []
    );
    return getReloadProm;
}

export class ViewAdapter extends ActionAdapter {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.vm = useService("view");
        this.shouldUpdateWidget = true;
        this.magicReload = useMagicLegacyReload();
        const debugContext = {
            action: this.props.viewParams.action,
            component: this,
        };
        useDebugCategory("action", debugContext);
        useDebugCategory("view", debugContext);
        if (this.props.viewInfo.type === "form") {
            useDebugCategory("form", debugContext);
        }
        this.env = Component.env;
    }

    get actionId() {
        return this.props.viewParams.action.jsId;
    }

    async willStart() {
        if (this.props.widget) {
            this.widget = this.props.widget;
            this.widget.setParent(this);
            if (this.props.onReverseBreadcrumb) {
                await this.props.onReverseBreadcrumb();
            }
            return this.updateWidget(this.props.viewParams);
        } else {
            const view = new this.props.View(this.props.viewInfo, this.props.viewParams);
            this.widget = await view.getController(this);
            if (this.__owl__.status === 5 /* DESTROYED */) {
                // the component might have been destroyed meanwhile, but if so, `this.widget` wasn't
                // destroyed by OwlCompatibility layer as it wasn't set yet, so destroy it now
                if (!this.actionService.__legacy__isActionInStack(this.actionId)) {
                    this.widget.destroy();
                }
                return Promise.resolve();
            }
            return this.widget._widgetRenderAndInsert(() => {});
        }
    }

    /**
     * @override
     */
    async updateWidget() {
        const shouldUpdateWidget = this.shouldUpdateWidget;
        this.shouldUpdateWidget = true;
        if (!shouldUpdateWidget) {
            return this.magicReload();
        }
        await this.widget.willRestore();
        const options = Object.assign({}, this.props.viewParams, {
            shouldUpdateSearchComponents: true,
        });
        if (!this.magicReload()) {
            this.widget.reload(options);
        }
        return this.magicReload();
    }

    /**
     * Override to add the state of the legacy controller in the exported state.
     */
    exportState() {
        const state = super.exportState();
        const widgetState = this.__widget.exportState();
        return Object.assign({}, state, widgetState);
    }

    async loadViews(resModel, context, views) {
        return (await this.vm.loadViews({ resModel, views, context }, {})).__legacy__.fields_views;
    }

    /**
     * @private
     * @param {OdooEvent} ev
     */
    async _trigger_up(ev) {
        const payload = ev.data;
        if (ev.name === "switch_view") {
            try {
                const props = {};
                if (payload.mode) {
                    props.mode = payload.mode;
                }
                // if (payload.res_id) {
                // if make 'open a record, come back, and create a new record' crash
                props.resId = payload.res_id;
                // }
                await this.actionService.switchView(payload.view_type, props);
            } catch (e) {
                if (e instanceof ViewNotFoundError) {
                    return;
                }
                throw e;
            }
        } else if (ev.name === "execute_action") {
            const buttonContext = new Context(payload.action_data.context).eval();
            const envContext = new Context(payload.env.context).eval();
            wrapSuccessOrFail(
                this.actionService.doActionButton({
                    args: payload.action_data.args,
                    buttonContext: buttonContext,
                    context: envContext,
                    close: payload.action_data.close,
                    resModel: payload.env.model,
                    name: payload.action_data.name,
                    resId: payload.env.currentID || null,
                    resIds: payload.env.resIDs,
                    special: payload.action_data.special,
                    type: payload.action_data.type,
                    onClose: payload.on_closed,
                    effect: payload.action_data.effect,
                }),
                payload
            );
        } else {
            super._trigger_up(ev);
        }
    }
}
