/** @odoo-module **/

import Context from "web.Context";
import core from "web.core";
import { ComponentAdapter } from "web.OwlCompatibility";
import { objectToQuery } from "../core/browser/router_service";
import { useDebugMenu } from "../core/debug/debug_menu";
import { Dialog } from "../core/dialog/dialog";
import { useEffect } from "../core/effect_hook";
import { useService } from "../core/service_hook";
import { ViewNotFoundError } from "../webclient/actions/action_service";
import { cleanDomFromBootstrap, mapDoActionOptionAPI } from "./utils";

const { Component, tags } = owl;

function wrapSuccessOrFail(promise, { on_success, on_fail } = {}) {
    return promise.then(on_success || (() => {})).catch((reason) => {
        if (on_fail) {
            on_fail(reason);
        }
        if (reason instanceof Error) {
            throw reason;
        }
    });
}

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
                this.title.setParts({ action: this.widget.getTitle() });
                const query = objectToQuery(this.widget.getState());
                Object.assign(query, this.tempQuery);
                this.tempQuery = null;
                this.__widget = this.widget;
                if (!this.wowlEnv.inDialog) {
                    this.router.pushState(query);
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
                this.trigger("controller-title-updated", this.__widget.getTitle());
                core.bus.trigger("DOM_updated");

                return () => {
                    this.__widget.updateControlPanel = originalUpdateControlPanel;
                    this.wowlEnv.bus.off("ACTION_MANAGER:UPDATE", this);
                };
            },
            () => []
        );
    }

    _trigger_up(ev) {
        const payload = ev.data;
        if (ev.name === "do_action") {
            if (payload.action.context) {
                payload.action.context = new Context(payload.action.context).eval();
            }
            this.onReverseBreadcrumb = ev.data.options && ev.data.options.on_reverse_breadcrumb;
            const legacyOptions = mapDoActionOptionAPI(ev.data.options);
            wrapSuccessOrFail(this.actionService.doAction(payload.action, legacyOptions), payload);
        } else if (ev.name === "breadcrumb_clicked") {
            this.actionService.restore(payload.controllerID);
        } else if (ev.name === "push_state") {
            const query = objectToQuery(payload.state);
            if (this.tempQuery) {
                Object.assign(this.tempQuery, query);
                return;
            }
            this.router.pushState(query);
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
                WarningDialog.bodyTemplate = tags.xml`<t t-esc="props.message"/>`;
                this.dialogs.open(WarningDialog, {
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
}

export class ClientActionAdapter extends ActionAdapter {
    setup() {
        super.setup();
        useDebugMenu("action", { action: this.props.widgetArgs[0] });
        this.env = Component.env;
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

    do_push_state() {}
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
                return legacyReloadProm.then(() => {
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
                return updateProm.then(() => {
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
        useDebugMenu("action", {
            action: this.props.viewParams.action,
            component: this,
        });
        useDebugMenu("view");
        if (this.props.viewInfo.type === "form") {
            useDebugMenu("form");
        }
        this.env = Component.env;
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
                this.widget.destroy();
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

    async loadViews(model, context, views) {
        return (await this.vm.loadViews({ model, views, context }, {})).fields_views;
    }

    /**
     * @private
     * @param {OdooEvent} ev
     */
    async _trigger_up(ev) {
        const payload = ev.data;
        if (ev.name === "switch_view") {
            const state = ev.target.exportState();
            try {
                await this.actionService.switchView(payload.view_type, {
                    recordId: payload.res_id,
                    recordIds: state.resIds,
                    searchModel: state.searchModel,
                    searchPanel: state.searchPanel,
                    mode: payload.mode,
                });
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
                    model: payload.env.model,
                    name: payload.action_data.name,
                    recordId: payload.env.currentID || null,
                    recordIds: payload.env.resIDs,
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
