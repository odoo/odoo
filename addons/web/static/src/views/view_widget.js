/* @odoo-module */

import { registry } from "@web/core/registry";
import { decodeObjectForTemplate } from "@web/views/helpers/view_compiler";

const { Component, xml } = owl;
const viewWidgetRegistry = registry.category("view_widgets");

/**
 * A Component that supports rendering `<widget />` tags in a view arch
 * It should have minimum legacy support that is:
 * - getting the legacy widget class from the legacy registry
 * - instanciating a legacy widget
 * - passing to it a "legacy node", which is a representation of the arch's node
 * It supports instancing components from the "view_widgets" registry.
 */
export class ViewWidget extends Component {
    get Widget() {
        return viewWidgetRegistry.get(this.props.name);
    }

    get widgetProps() {
        const { record, node: rawNode, options } = this.props;
        const node = rawNode ? decodeObjectForTemplate(rawNode) : {};
        return { record, node, options: options || {} };
    }
}
ViewWidget.template = xml/*xml*/ `
    <div class="o_widget" t-att-class="props.class" t-att-style="props.style">
        <t t-component="Widget" t-props="widgetProps" />
    </div>`;
