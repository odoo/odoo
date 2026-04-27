/** @odoo-module **/

import { registry } from "@web/core/registry";

import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

export class CancellationReason extends SelectionField {

    get availableOptions() {
        return this.props.record.data.available_cancellation_reasons.split(",");
    }

    /** Override **/
    get options() {
        const availableOptions = this.availableOptions;
        return super.options.filter(x => availableOptions.includes(x[0]));
    }

}

registry.category("fields").add("l10n_mx_edi_cancellation_reason", {
    ...selectionField,
    component: CancellationReason,
});
