import { evaluateExpr, evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";

import { Component, t, xml } from "@odoo/owl";
const viewWidgetRegistry = registry.category("view_widgets");

const supportedInfoValidation = t.array(
    t.object({
        label: t.string(),
        name: t.string(),
        type: t.string(),
        availableTypes: t.array(t.string()).optional(),
        default: t.any().optional(),
        help: t.string().optional(),
        choices: /* choices if type == selection */ t
            .array(
                t.object({
                    label: t.string(),
                    value: t.any(),
                })
            )
            .optional(),
    })
);

viewWidgetRegistry.addValidation(
    t.object({
        component: t.component(),
        extractProps: t.function().optional(),
        additionalClasses: t.array(t.string()).optional(),
        fieldDependencies: t
            .or([t.function(), t.array(t.object({ name: t.string(), type: t.string() }))])
            .optional(),
        listViewWidth: t
            .or([
                t.number(),
                t.tuple([t.number()]),
                t.tuple([t.number(), t.number()]),
                t.function(),
            ])
            .optional(),
        supportedAttributes: supportedInfoValidation.optional(),
        supportedOptions: supportedInfoValidation.optional(),
    })
);

/**
 * A Component that supports rendering `<widget />` tags in a view arch
 * It should have minimum legacy support that is:
 * - getting the legacy widget class from the legacy registry
 * - instanciating a legacy widget
 * - passing to it a "legacy node", which is a representation of the arch's node
 * It supports instancing components from the "view_widgets" registry.
 */
export class Widget extends Component {
    static template = xml/*xml*/ `
        <div t-att-class="this.classNames" t-att-style="this.props.style">
            <t t-component="this.widget.component" t-props="this.widgetProps" />
        </div>`;

    static parseWidgetNode = function (node) {
        const name = node.getAttribute("name");
        const widget = viewWidgetRegistry.get(name);
        const widgetInfo = {
            name,
            widget,
            options: {},
            attrs: {},
        };

        for (const { name, value } of node.attributes) {
            if (["name", "widget"].includes(name)) {
                // avoid adding name and widget to attrs
                continue;
            }
            if (name === "options") {
                widgetInfo.options = evaluateExpr(value);
            } else if (!name.startsWith("t-att")) {
                if (["column_invisible", "invisible"].includes(name)) {
                    widgetInfo[name] = value;
                }
                // all other (non dynamic) attributes
                widgetInfo.attrs[name] = value;
            }
        }

        return widgetInfo;
    };
    static props = {
        "*": true,
    };

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

        let readonlyFromModifiers = false;
        let propsFromNode = {};
        if (this.props.widgetInfo) {
            const widgetInfo = this.props.widgetInfo;
            readonlyFromModifiers = evaluateBooleanExpr(
                widgetInfo.attrs.readonly,
                record.evalContextWithVirtualIds
            );
            const dynamicInfo = {
                readonly: readonlyFromModifiers,
            };
            propsFromNode = this.widget.extractProps
                ? this.widget.extractProps(widgetInfo, dynamicInfo)
                : {};
        }
        return {
            record,
            readonly: !record.isInEdition || readonlyFromModifiers || false,
            ...propsFromNode,
        };
    }
}
