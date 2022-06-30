/* @odoo-module */

import { registry } from "@web/core/registry";
import { decodeObjectForTemplate } from "@web/views/view_compiler";

const { Component, xml } = owl;
const viewWidgetRegistry = registry.category("view_widgets");

function findWidgetComponent(name) {
    return viewWidgetRegistry.get(name);
}

/**
 * A Component that supports rendering `<widget />` tags in a view arch
 * It should have minimum legacy support that is:
 * - getting the legacy widget class from the legacy registry
 * - instanciating a legacy widget
 * - passing to it a "legacy node", which is a representation of the arch's node
 * It supports instancing components from the "view_widgets" registry.
 */
export class Widget extends Component {
    get Widget() {
        return findWidgetComponent(this.props.name);
    }

    get widgetProps() {
        const { record, node: rawNode, options, readonly } = this.props;
        const node = rawNode ? decodeObjectForTemplate(rawNode) : {};
        return { record, node, options: options || {}, readonly };
    }
}
Widget.template = xml/*xml*/ `
    <div class="o_widget" t-att-class="props.className" t-att-style="props.style">
        <t t-component="Widget" t-props="widgetProps" />
    </div>`;

Widget.parseWidgetNode = function (node) {
    const name = node.getAttribute("name");
    const component = findWidgetComponent(name);
    return {
        name,
        component,
        fieldDependencies: { ...component.fieldDependencies },
    };
};
