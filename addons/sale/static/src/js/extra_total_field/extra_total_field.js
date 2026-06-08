import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { formatMonetary } from "@web/views/fields/formatters";

export class ExtraTotalsField extends Component {
    static template = "sale.ExtraTotalsField";

    static props = standardFieldProps;

    formatMonetary(amount) {
        return formatMonetary(amount, {
            currencyId: this.props.record.data.currency_id.id,
        });
    }

    get groups() {
        return this.props.record.data[this.props.name].sort(
            (a, b) => (a.sequence ?? Infinity) - (b.sequence ?? Infinity)
        );
    }
}

registry.category("fields").add("sale-extra-totals", {
    component: ExtraTotalsField,
});
