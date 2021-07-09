/** @odoo-module **/
import { useBus } from "@web/core/bus_hook";

const { Component, hooks, tags } = owl;

export class ActionController extends Component {
    setup() {
        this.Component = this.props.controller.Component;
        this.componentRef = hooks.useRef("component");
        this.registerCallback = null;
        if (this.props.controller.action.target !== "new") {
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
        this.props.actionControllerCallbacks.onCatchError(error);
    }
    mounted() {
        this.props.actionControllerCallbacks.onMounted();
    }
    willUnmount() {
        this.props.actionControllerCallbacks.onWillUnmount();
    }
    onHistoryBack() {
        this.props.actionControllerCallbacks.onHistoryBack();
    }
    onTitleUpdated(ev) {
        this.props.actionControllerCallbacks.onTitleUpdated(ev);
    }
}
ActionController.template = tags.xml`<t t-component="Component" t-props="props"
registerCallback="registerCallback"
t-ref="component"
t-on-history-back="onHistoryBack"
t-on-controller-title-updated.stop="onTitleUpdated"/>`;
