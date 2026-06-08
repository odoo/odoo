import { Component, props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { percentPieField } from "@web/views/fields/percent_pie/percent_pie_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class DeliverancePercentPieField extends Component {
    static template = "mass_mailing.DeliverancePercentPieField";

    props = props({
        ...standardFieldProps,
        topFieldName: t.string(),
        bottomFieldName: t.string(),
    });
}

registry.category("fields").add("deliverance_percentpie", {
    additionalClasses: percentPieField.additionalClasses,
    component: DeliverancePercentPieField,
    extractProps: ({ attrs }) => ({
        topFieldName: attrs.top_field,
        bottomFieldName: attrs.bottom_field,
    }),
});
