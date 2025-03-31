/** @odoo-module */

import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class SoLineField extends Many2OneField {
    setup() {
        super.setup();

        const update = this.update;
        this.update = (value, params = {}) => {
            update(value, params);
            if ( // field is unset AND the old & new so_lines are different
                !this.props.record.data.is_so_line_edited &&
                this.value[0] != value[0]?.id
            ) {
                this.props.record.update({ is_so_line_edited: true });
            }
        };
    }
}

export const soLineField = {
    ...many2OneField,
    component: SoLineField,
};
registry.category("fields").add("so_line_field", soLineField);

export class TimesheetsOne2ManyField extends X2ManyField {}
export const timesheetsOne2ManyField = {
    ...x2ManyField,
    component: TimesheetsOne2ManyField,
    additionalClasses: ['o_field_one2many'],
};
