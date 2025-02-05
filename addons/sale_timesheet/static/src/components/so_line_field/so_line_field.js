import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Many2One, useMany2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class SoLineField extends Component {
    static template = "sale_timesheet.SoLineField";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    setup() {
        this.m2o = useMany2One(() => this.props);
    }

    get m2oProps() {
        return {
            ...this.m2o.computeProps(),
            update: (value) => {
                const otherChanges = {};
                if (
                    // field is unset AND the old & new so_lines are different
                    !this.props.record.data.is_so_line_edited &&
                    this.m2o.value[0] != value[0]?.id
                ) {
                    otherChanges.is_so_line_edited = true;
                }
                return this.m2o.update(value, otherChanges);
            },
        };
    }
}

registry.category("fields").add("so_line_field", {
    ...buildM2OFieldDescription(SoLineField),
});
