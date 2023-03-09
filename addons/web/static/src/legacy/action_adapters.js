/** @odoo-module **/

import Context from "web.Context";
import core from "web.core";
import { ComponentAdapter } from "web.OwlCompatibility";
import { objectToQuery } from "../core/browser/router_service";
import { useDebugCategory } from "../core/debug/debug_context";
import { Dialog } from "../core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { cleanDomFromBootstrap, wrapSuccessOrFail, useLegacyRefs } from "./utils";
import { mapDoActionOptionAPI } from "./backend_utils";

import {
    Component,
    onMounted,
    onWillUnmount,
    onWillUpdateProps,
    useEffect,
    useExternalListener,
    xml,
} from "@odoo/owl";

class WarningDialog extends Component {}
WarningDialog.template = xml`<Dialog title="props.title">
    <p style="white-space:pre-wrap" t-esc="props.message"/>
</Dialog>`;
WarningDialog.components = { Dialog };

class ActionAdapter extends ComponentAdapter {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.router = useService("router");
        this.title = useService("title");
        this.notifications = useService("notification");
        this.dialogs = useService("dialog");
        this.wowlEnv = this.env;
        const legacyRefs = useLegacyRefs();
        legacyRefs.component = this;
        // a legacy widget widget can push_state anytime including during its async rendering
        // In Wowl, we want to have all states pushed during the same setTimeout.
        // This is protected in legacy (backward compatibility) but should not e supported in Wowl
        this.tempQuery = {};
        let originalUpdateControlPanel;
        useEffect(
            () => {
                legacyRefs.widget = this.widget;
                const query = this.widget.getState();
                Object.assign(query, this.tempQuery);
                this.tempQuery = null;
                this.__widget = this.widget;
                if (!this.wowlEnv.inDialog) {
                    this.pushState(query);
                }
                const onActionManagerUpdate = () => {
                    this.env.bus.trigger("close_dialogs");
                    cleanDomFromBootstrap();
                };
                this.wowlEnv.bus.addEventListener("ACTION_MANAGER:UPDATE", onActionManagerUpdate);
                originalUpdateControlPanel = this.__widget.updateControlPanel.bind(this.__widget);
                this.__widget.updateControlPanel = (newProps) => {
                    this.wowlEnv.config.setDisplayName(this.__widget.getTitle());
                    return originalUpdateControlPanel(newProps);
                };
                core.bus.trigger("DOM_updated");

                return () => {
                    this.__widget.updateControlPanel = originalUpdateControlPanel;
                    this.wowlEnv.bus.removeEventListener(
                        "ACTION_MANAGER:UPDATE",
                        onActionManagerUpdate
                    );
                };
            },
            () => []
        );
        useExternalListener(window, "click", () => {
            cleanDomFromBootstrap();
        });

        onWillUpdateProps(() => {
            if (this.widget === null) {
                this.widget = this.__widget;
            }
        });
        onWillUnmount(() => {
            if (this.__widget && this.__widget.on_detach_callback) {
                this.__widget.on_detach_callback();
            }
        });

        this.onScrollTo = (payload) => {
            const contentEl = this.el.querySelector(".o_content");
            if (contentEl) {
                contentEl.scrollLeft = payload.left || 0;
                contentEl.scrollTop = payload.top || 0;
            }
        };
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
                this.wowlEnv.config.setDisplayName(actionTitle);
            }
        }
        if (this.props.onPushState) {
            this.props.onPushState(query);
        } else {
            this.router.pushState(query);
        }
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
        } else if (ev.name === "history_back") {
            this.wowlEnv.config.historyBack();
        } else if (ev.name === "scrollTo") {
            this.onScrollTo(payload);
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

    __destroy() {
        if (this.actionService.__legacy__isActionInStack(this.actionId)) {
            this.widget = null;
        }
        super.__destroy(...arguments);
    }
    get el() {
        return (this.widget || this.__widget).el;
    }
}

export class ClientActionAdapter extends ActionAdapter {
    setup() {
        super.setup();
        useDebugCategory("action", { action: this.props.widgetArgs[0] });
        onMounted(() => {
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

    async onWillStart() {
        if (this.props.widget) {
            this.widget = this.props.widget;
            this.widget.setParent(this);
            if (this.props.onReverseBreadcrumb) {
                await this.props.onReverseBreadcrumb();
            }
            return this.updateWidget();
        }
        return super.onWillStart();
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
