/** @odoo-module */

import { registry } from "@web/core/registry";
import { formatFloatFactor } from "@web/views/fields/formatters";
import { GridCell } from "./grid_cell";

function formatter(value, options = {}) {
    return formatFloatFactor(value, options);
}

export class FloatFactorGridCell extends GridCell {
    static props = {
        ...GridCell.props,
        factor: { type: Number, optional: true },
    };

    parse(value) {
        const factorValue = value / this.factor;
        return super.parse(factorValue.toString());
    }

    get factor() {
        return this.props.factor || this.props.fieldInfo.options?.factor || 1;
    }

    get value() {
        return super.value * this.factor;
    }

    get formattedValue() {
        return formatter(this.value);
    }
}

export const floatFactorGridCell = {
    component: FloatFactorGridCell,
    formatter,
};

registry.category("grid_components").add("float_factor", floatFactorGridCell);
