import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class SoLineField extends Component {
    static template = "sale_timesheet.SoLineField";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            update: (value) => {
                this.props.record.update({ [this.props.name]: value });
                if (
                    // field is unset AND the old & new so_lines are different
                    !this.props.record.data.is_so_line_edited &&
                    this.props.record.data[this.props.name].id != value.id
                ) {
                    this.props.record.update({ is_so_line_edited: true });
                }
            },
        };
    }
}

registry.category("fields").add("so_line_field", {
    ...buildM2OFieldDescription(SoLineField),
});
