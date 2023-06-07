/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

class AttachmentNumber extends Component {

    setup() {
        super.setup();
        this.attachment_number = this.props.record.data.attachment_number
    }
    static template = "hr_expense.AttachmentNumber"
}

registry.category("fields").add("attachment_number", {component: AttachmentNumber});
