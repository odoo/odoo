/** @odoo-module */

import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

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

registry.category("fields").add('so_line_one2many', registry.category('fields').get("one2many")); // TODO: Remove me when the gantt view is converted in OWL
registry.category("fields").add("so_line_field", SoLineField);
