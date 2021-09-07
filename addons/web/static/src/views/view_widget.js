/* @odoo-module */
import widgetRegistry from "web.widget_registry";
import widgetRegistryOwl from "web.widgetRegistry";
import { registry } from "@web/core/registry";
import { ComponentAdapter } from "web.OwlCompatibility";
import { decodeObjectForTemplate } from "@web/views/compile/compile_lib";

import { useEffect } from "@web/core/utils/hooks";

export class ViewWidget extends owl.Component {
    setup() {
        this.wowlEnv = this.env;
        this.renderId = 1;
        useEffect(() => {
            this.renderId++;
        });
        const widgetName = this.props.widgetName;
        const Widget = registry.category("view_widgets").get(widgetName, null);
        if (!Widget) {
            this.isLegacyOwl = true;
            this.env = owl.Component.env;
        }
        this.Widget = Widget || widgetRegistryOwl.get(widgetName) || widgetRegistry.get(widgetName);
        this.isLegacy = !(this.Widget instanceof owl.Component);
    }

    get widgetProps() {
        if (!this.isLegacyOwl) {
            return this.props;
        } else {
            throw new Error("To implement ....");
        }
    }

    get widgetArgs() {
        const record = this.props.model._legacyRecord_;
        const node = this.props._legacyNode_
            ? decodeObjectForTemplate(this.props._legacyNode_)
            : {};
        node.name = this.props.widgetName;
        if (this.props.title) {
            node.attrs = Object.assign(node.attrs || {}, { title: this.props.title });
        }
        return [record, node];
    }
}
ViewWidget.template = owl.tags.xml/*xml*/ `<t>
    <ComponentAdapter t-if="isLegacy" Component="Widget" widgetArgs="widgetArgs" t-key="renderId" class="o_widget" />
    <t t-else="" t-component="Widget" t-props="widgetProps" class="o_widget" />
</t>
`;
ViewWidget.components = { ComponentAdapter };
