/* @odoo-module */

import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { evalDomain } from "@web/views/utils";

import { Component, xml } from "@odoo/owl";
const viewWidgetRegistry = registry.category("view_widgets");

/**
 * A Component that supports rendering `<widget />` tags in a view arch
 * It should have minimum legacy support that is:
 * - getting the legacy widget class from the legacy registry
 * - instanciating a legacy widget
 * - passing to it a "legacy node", which is a representation of the arch's node
 * It supports instancing components from the "view_widgets" registry.
 */
export class Widget extends Component {
    setup() {
        if (this.props.widgetInfo) {
            this.widget = this.props.widgetInfo.widget;
        } else {
            this.widget = viewWidgetRegistry.get(this.props.name);
        }
    }

    get classNames() {
        const classNames = {
            o_widget: true,
            [`o_widget_${this.props.name}`]: true,
            [this.props.className]: Boolean(this.props.className),
        };
        if (this.widget.additionalClasses) {
            for (const cls of this.widget.additionalClasses) {
                classNames[cls] = true;
            }
        }
        return classNames;
    }
    get widgetProps() {
        const record = this.props.record;
        const evalContext = record.evalContext;

        let readonlyFromModifiers = false;
        let propsFromNode = {};
        if (this.props.widgetInfo) {
            const widgetInfo = this.props.widgetInfo;
            const modifiers = widgetInfo.modifiers || {};
            readonlyFromModifiers = evalDomain(modifiers.readonly, evalContext);
            propsFromNode = this.widget.extractProps ? this.widget.extractProps(widgetInfo) : {};
        }

        return {
            record,
            readonly: !record.isInEdition || readonlyFromModifiers || false,
            ...propsFromNode,
        };
    }
}
Widget.template = xml/*xml*/ `
    <div t-att-class="classNames" t-att-style="props.style">
        <t t-component="widget.component" t-props="widgetProps" />
    </div>`;

Widget.parseWidgetNode = function (node) {
    const name = node.getAttribute("name");
    const widget = viewWidgetRegistry.get(name);

    const widgetInfo = {
        name,
        modifiers: JSON.parse(node.getAttribute("modifiers") || "{}"),
        widget,
        options: evaluateExpr(node.getAttribute("options") || "{}"),
        attrs: {}, // populated below
    };

    for (const { name, value } of node.attributes) {
        if (!name.startsWith("t-att")) {
            // all other (non dynamic) attributes
            widgetInfo.attrs[name] = value;
        }
    }

    return widgetInfo;
};
Widget.props = {
    "*": true,
};
