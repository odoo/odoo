/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { action_registry as legacyActionRegistry } from "web.core";
import Widget from "web.Widget";
import { useSetupAction } from "../webclient/actions/action_hook";
import { ClientActionAdapter } from "./action_adapters";
import { breadcrumbsToLegacy } from "./backend_utils";
import { useLegacyRefs } from "./utils";
import { LegacyComponent } from "./legacy_component";

const { xml } = owl;
const actionRegistry = registry.category("actions");

const legacyClientActionTemplate = xml`
    <ClientActionAdapter Component="Widget" widgetArgs="widgetArgs" widget="widget"
                         onReverseBreadcrumb="onReverseBreadcrumb"/>`;

// registers an action from the legacy action registry to the wowl one, ensuring
// that widget actions are actually Components
function registerClientAction(name, action) {
    if (action.prototype instanceof Widget) {
        // the action is a widget, wrap it into a Component and register that component
        class Action extends LegacyComponent {
            setup() {
                this.Widget = action;
                const options = {};
                for (const key in this.props) {
                    if (key === "action" || key === "actionId") {
                        continue;
                    } else {
                        options[key] = this.props[key];
                    }
                }

                const legacyRefs = useLegacyRefs();

                if (this.env.config.breadcrumbs) {
                    options.breadcrumbs = breadcrumbsToLegacy(this.env.config.breadcrumbs);
                }

                // always add user context to the action context
                this.user = useService("user");
                const clientAction = Object.assign({}, this.props.action, {
                    context: Object.assign({}, this.user.context, this.props.action.context),
                });

                this.widgetArgs = [clientAction, options];
                this.widget = this.props.state && this.props.state.__legacy_widget__;
                this.onReverseBreadcrumb =
                    this.props.state && this.props.state.__on_reverse_breadcrumb__;
                useSetupAction({
                    beforeLeave: () => legacyRefs.widget.canBeRemoved(),
                    getLocalState: () => legacyRefs.component.exportState(),
                });
            }
        }
        Action.template = legacyClientActionTemplate;
        Action.components = { ClientActionAdapter };
        Action.isLegacy = true;
        Action.target = action.prototype.target;
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
