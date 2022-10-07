/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

export class PercentPieField extends Component {
    get transform() {
        const rotateDeg = (360 * this.props.value) / 100;
        return {
            left: rotateDeg < 180 ? 180 : rotateDeg,
            right: rotateDeg < 180 ? rotateDeg : 0,
            value: rotateDeg,
        };
    }
}

PercentPieField.template = "web.PercentPieField";
PercentPieField.props = {
    ...standardFieldProps,
    string: { type: String, optional: true },
};

PercentPieField.displayName = _lt("PercentPie");
PercentPieField.supportedTypes = ["float", "integer"];

PercentPieField.extractProps = ({ attrs }) => {
    return {
        string: attrs.string,
    };
};
PercentPieField.additionalClasses = ["o_field_percent_pie"];

registry.category("fields").add("percentpie", PercentPieField);
