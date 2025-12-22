/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class AttachmentNumber extends Component {
    static template = "hr_expense.AttachmentNumber";
    static props = {...standardFieldProps};

    setup() {
        super.setup();
        this.nb_attachment = this.props.record.data.nb_attachment
    }
}

registry.category("fields").add("nb_attachment", {component: AttachmentNumber});
