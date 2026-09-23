// @ts-check
/** @odoo-module native */

import {
    Component,
    onError,
    onMounted,
    onWillDestroy,
    onWillUnmount,
    status,
    useChildSubEnv,
    xml,
} from "@odoo/owl";
import { CallbackRecorder } from "@web/core/action_hook";
import { useDebugCategory } from "@web/core/debug/debug_context";
import { AppEvent } from "@web/core/events";
import { useBus } from "@web/core/utils/hooks";
import { View } from "@web/views/view";

const ControllerComponentTemplate = xml`<t t-component="this.Component" t-props="this.componentProps"/>`;

/** @import { ActionManager } from "./action_service.js" */

/**
 * @param {any} component
 * @param {any} action
 * @param {ActionManager} am
 */
function useControllerStateRecorders(component, action, am) {
    if (action.target === "new") {
        return;
    }
    component.__beforeLeave__ = new CallbackRecorder();
    component.__getGlobalState__ = new CallbackRecorder();
    component.__getLocalState__ = new CallbackRecorder();
    useBus(am.env.bus, AppEvent.CLEAR_UNCOMMITTED_CHANGES, (ev) => {
        ev.detail.push(...component.__beforeLeave__.callbacks);
    });
    if (component.Component !== View) {
        useChildSubEnv({
            __beforeLeave__: component.__beforeLeave__,
            __getGlobalState__: component.__getGlobalState__,
            __getLocalState__: component.__getLocalState__,
        });
    }
}

/** @param {ActionManager} am */
export function makeControllerComponent(am) {
    return class ControllerComponent extends Component {
        static template = ControllerComponentTemplate;
        static props = {
            dispatch: { type: Object },
            updateActionState: { type: Function, optional: true },
            "*": true,
        };

        setup() {
            const { controller, action, nextStack } = this.props.dispatch;
            this.Component = controller.Component;
            useDebugCategory("action", { action });
            useChildSubEnv({
                config: controller.config,
                pushStateBeforeReload: () => {
                    if (controller.isMounted) {
                        return;
                    }
                    am.pushState(nextStack, { sync: true });
                },
            });
            useControllerStateRecorders(this, action, am);
            onMounted(this.onMounted);
            onWillUnmount(this.onWillUnmount);
            onWillDestroy(this.onWillDestroy);
            onError(this.onError);
        }

        /** @param {CallbackRecorder} recorder */
        _makeStateExporter(recorder) {
            if (!recorder) {
                return undefined;
            }
            return () => {
                const exportFns = recorder.callbacks;
                if (exportFns.length) {
                    return Object.assign({}, ...exportFns.map((fn) => fn()));
                }
            };
        }

        onMounted() {
            this.props.dispatch.commit({
                getGlobalState: this._makeStateExporter(this.__getGlobalState__),
                getLocalState: this._makeStateExporter(this.__getLocalState__),
            });
        }

        /** @param {any} error */
        onError(error) {
            return this.props.dispatch.fail(error, { componentStatus: status(this) });
        }

        onWillDestroy() {
            this.props.dispatch.discard({ componentStatus: status(this) });
        }

        onWillUnmount() {
            this.props.dispatch.controller.isMounted = false;
        }

        get componentProps() {
            const { dispatch, ...componentProps } = this.props;
            const { controller } = dispatch;
            const updateActionState = componentProps.updateActionState;
            if (updateActionState) {
                componentProps.updateActionState = (/** @type {any} */ newState) =>
                    updateActionState(controller, newState);
            }
            if (this.Component === View) {
                componentProps.__beforeLeave__ = this.__beforeLeave__;
                componentProps.__getGlobalState__ = this.__getGlobalState__;
                componentProps.__getLocalState__ = this.__getLocalState__;
            }
            return componentProps;
        }
    };
}
