/** @odoo-module **/

import {registry} from "@web/core/registry";
import {standardWidgetProps} from "@web/views/widgets/standard_widget_props";
import {Component, onWillUpdateProps, useState} from "@odoo/owl";
import {getTooltipInfo} from "@web/views/fields/field_tooltip";

class LocalizedLabel extends Component {
    setup() {
        super.setup();
        this.field = this.props.record.fields[this.props.for];
        this.state = useState({term: this.props.record.data[this.props.label_compute_field]});

        onWillUpdateProps((nextProps) => {
            const nextLabel = nextProps.record.data[this.props.label_compute_field];
            if (this.state.term !== nextLabel) {
                this.state.term = nextLabel;
            }
        });
    }

    get tooltipInfo() {
        if (this.field) {
            const fieldInfo = this.props.record.activeFields[this.props.for];
            const tooltip = getTooltipInfo({
                field: this.field,
                fieldInfo: fieldInfo,
            });
            if (Boolean(odoo.debug) || (tooltip && JSON.parse(tooltip).field.help)) {
                return tooltip;
            }
        }
        return false;
    }
}

LocalizedLabel.template = "account.LocalizedLabel";
LocalizedLabel.props = {
    ...standardWidgetProps,
    // Set this to the name of the compute field holding the label string.
    label_compute_field: {type: String},
    // Set this to the name of the field the label is for. We can use it to recreate the tooltip.
    for: {type: String},
};

export const localizedLabel = {
    component: LocalizedLabel,
    extractProps: ({attrs}) => ({
        label_compute_field: attrs.label_compute_field,
        for: attrs.for,
    })
};

registry.category("view_widgets").add("localized_label", localizedLabel);
