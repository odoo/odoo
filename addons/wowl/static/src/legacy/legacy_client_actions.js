/** @odoo-module **/

import { actionRegistry } from "../actions/action_registry";
import { action_registry as legacyActionRegistry } from "web.core";
import { ClientActionAdapter } from "./action_adapters";
import Widget from "web.Widget";
import { breadcrumbsToLegacy } from "./utils";
import { useSetupAction } from "../actions/action_manager";

const { Component, hooks, tags } = owl;

// registers an action from the legacy action registry to the wowl one, ensuring
// that widget actions are actually Components
function registerClientAction(name, action) {
  if (action.prototype instanceof Widget) {
    // the action is a widget, wrap it into a Component and register that component
    class Action extends Component {
      constructor() {
        super(...arguments);
        this.controllerRef = hooks.useRef("controller");
        this.Widget = action;
        this.widgetArgs = [
          this.props.action,
          Object.assign({}, this.props.options, {
            breadcrumbs: breadcrumbsToLegacy(this.props.breadcrumbs),
          }),
        ];
        this.widget = this.props.state && this.props.state.__legacy_widget__;
        this.onReverseBreadcrumb = this.props.state && this.props.state.__on_reverse_breadcrumb__;
        const { scrollTo } = useSetupAction({
          beforeLeave: () => this.controllerRef.comp.widget.canBeRemoved(),
          export: () => this.controllerRef.comp.exportState(),
        });
        this.onScrollTo = (ev) => {
          scrollTo({ left: ev.detail.left, top: ev.detail.top });
        };
      }
    }
    Action.template = tags.xml`
      <ClientActionAdapter Component="Widget" widgetArgs="widgetArgs" widget="widget"
                           onReverseBreadcrumb="onReverseBreadcrumb" t-ref="controller"
                           t-on-scrollTo.stop="onScrollTo"/>
    `;
    Action.components = { ClientActionAdapter };
    Action.isLegacy = true;
    actionRegistry.add(name, Action);
  } else {
    // the action is either a Component or a function, register it directly
    actionRegistry.add(name, action);
  }
}

// register action already in the legacy registry, and listens to future registrations
for (const [name, action] of Object.entries(legacyActionRegistry.entries())) {
  if (!actionRegistry.contains(name)) {
    registerClientAction(name, action);
  }
}
legacyActionRegistry.onAdd(registerClientAction);
