/** @odoo-module */

import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";

export class SoLineField extends Many2OneField {
    setup() {
        super.setup();

        const update = this.update;
        this.update = (value, params = {}) => {
            update(value, params);
            if (value || this.updateOnEmpty) {
                this.props.record.update({ is_so_line_edited: true });
            }
        };
    }
}

export class TimesheetsOne2ManyField extends X2ManyField {}
TimesheetsOne2ManyField.additionalClasses = ['o_field_one2many'];
registry.category("fields").add('so_line_one2many', TimesheetsOne2ManyField); // TODO: Remove me when the gantt view is converted in OWL

registry.category("fields").add("so_line_field", SoLineField);
