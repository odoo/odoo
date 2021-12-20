/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";

const { Component } = owl;

const formatValue = (value) => {
    if (typeof value === "number") {
        return `${value % 1 === 0 ? value : value.toFixed(1)}%`;
    }
    return null;
};

export class PercentageEditor extends Component {
    get percentageValue() {
        return this.props.isPercentage ? this.props.value : 100 * this.props.value;
    }
}

PercentageEditor.template = "web.PercentageEditor";
PercentageEditor.props = {
    fieldClass: { type: String, optional: true },
    isPercentage: { type: Boolean, optional: true },
    onChange: { type: Function, optional: true },
    onKeydown: { type: Function, optional: true },
    value: String | Number,
};

export class PercentageViewer extends Component {
    get formattedValue() {
        return formatValue(this.props.isPercentage ? this.props.value : 100 * this.props.value);
    }
}

PercentageViewer.template = "web.PercentageViewer";
PercentageViewer.props = {
    fieldClass: { type: String, optional: true },
    isPercentage: { type: Boolean, optional: true },
    value: String | Number,
};
