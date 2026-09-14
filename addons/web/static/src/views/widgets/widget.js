// @ts-check
/** @odoo-module native */

import { Component, xml } from "@odoo/owl";
import { evaluateBooleanExpr, evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { FIELD_DEPENDENCIES_VALIDATION } from "@web/model/relational_model/field_metadata";
import { nodeAttrs } from "@web/views/ir/view_ir";
const viewWidgetRegistry = registry.category("view_widgets");

const supportedInfoValidation = {
    type: Array,
    element: {
        type: Object,
        shape: {
            name: String,
            type: String,
            "*": true,
        },
    },
    optional: true,
};

viewWidgetRegistry.addValidation({
    component: {
        validate: (/** @type {any} */ c) => c.prototype instanceof Component,
    },
    extractProps: { type: Function, optional: true },
    additionalClasses: { type: Array, element: String, optional: true },
    fieldDependencies: FIELD_DEPENDENCIES_VALIDATION,
    listViewWidth: {
        type: [
            Number,
            {
                type: Array,
                element: Number,
                validate: (/** @type {any[]} */ array) =>
                    array.length === 1 || array.length === 2,
            },
            Function,
        ],
        optional: true,
    },
    supportedAttributes: supportedInfoValidation,
    supportedOptions: supportedInfoValidation,
});

export class Widget extends Component {
    static template = xml`
        <div t-att-class="classNames" t-att-style="props.style">
            <t t-component="widget.component" t-props="widgetProps" />
        </div>`;

    /**
     * @param {import("@web/views/ir/view_ir_schema").ViewIRNode | Element} node
     * @returns {{ name: string, widget: Object, options: Object, attrs: Object }}
     */
    static parseWidgetNode = function (node) {
        const nodeAttributes = nodeAttrs(node);
        const name = /** @type {string} */ (nodeAttributes.name);
        const widget = viewWidgetRegistry.get(name);
        /** @type {{ name: any, widget: any, options: any, attrs: Record<string, any> }} */
        const widgetInfo = {
            name,
            widget,
            options: {},
            attrs: {},
        };

        for (const [name, value] of Object.entries(nodeAttributes)) {
            if (["name", "widget"].includes(name)) {
                continue;
            }
            if (name === "options") {
                widgetInfo.options = evaluateExpr(value);
            } else if (!name.startsWith("t-att")) {
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

    /** @returns {Record<string, boolean>} */
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
    /** @returns {Object} */
    get widgetProps() {
        const record = this.props.record;

        let readonlyFromModifiers = false;
        let propsFromNode = {};
        if (this.props.widgetInfo) {
            const widgetInfo = this.props.widgetInfo;
            readonlyFromModifiers = evaluateBooleanExpr(
                widgetInfo.attrs.readonly,
                record.evalContextWithVirtualIds,
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
