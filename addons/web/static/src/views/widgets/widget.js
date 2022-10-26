/* @odoo-module */

import { evaluateExpr } from "@web/core/py_js/py";
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

    get classNames() {
        return {
            o_widget: true,
            [`o_widget_${this.props.name}`]: true,
            [this.props.className]: Boolean(this.props.className),
        };
    }
    get widgetProps() {
        const { node: rawNode } = this.props;
        const node = rawNode ? decodeObjectForTemplate(rawNode) : {};
        let propsFromAttrs = {};
        if (node.attrs) {
            const extractProps = this.Widget.extractProps || (() => ({}));
            propsFromAttrs = extractProps({
                attrs: {
                    ...node.attrs,
                    options: evaluateExpr(node.attrs.options || "{}"),
                },
            });
        }
        const props = { ...this.props };
        delete props.class;
        delete props.name;
        delete props.node;

        return { ...propsFromAttrs, ...props };
    }
}
Widget.template = xml/*xml*/ `
    <div t-att-class="classNames" t-att-style="props.style">
        <t t-component="Widget" t-props="widgetProps" />
    </div>`;

Widget.parseWidgetNode = function (node) {
    const name = node.getAttribute("name");
    const WidgetComponent = findWidgetComponent(name);
    const attrs = Object.fromEntries(
        [...node.attributes].map(({ name, value }) => {
            return [name, name === "modifiers" ? JSON.parse(value || "{}") : value];
        })
    );
    return {
        options: evaluateExpr(node.getAttribute("options") || "{}"),
        name,
        rawAttrs: attrs,
        WidgetComponent,
    };
};
