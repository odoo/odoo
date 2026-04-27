/** @odoo-module */

import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class GridRow extends Component {
    static template = "web_grid.GridRow";
    static props = {
        name: String,
        model: Object,
        row: Object,
        classNames: { type: String, optional: true },
        context: { type: Object, optional: true },
        style: { type: String, optional: true },
        value: { optional: true },
    };
    static defaultProps = {
        classNames: "",
        context: {},
        style: "",
    };

    get value() {
        let value = 'value' in this.props ? this.props.value : this.props.row.initialRecordValues[this.props.name];
        const fieldInfo = this.props.model.fieldsInfo[this.props.name];
        if (fieldInfo.type === "selection") {
            value = fieldInfo.selection.find(([key,]) => key === value)?.[1];
        }
        return value;
    }
}

export const gridRow = {
    component: GridRow,
};

registry
    .category("grid_components")
    .add("selection", gridRow)
    .add("char", gridRow);
