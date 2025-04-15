/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

class AttachmentNumber extends Component {

    setup() {
        super.setup();
        this.nb_attachment = this.props.record.data.nb_attachment
    }
    static template = "hr_expense.AttachmentNumber"
}

registry.category("fields").add("nb_attachment", {component: AttachmentNumber});
