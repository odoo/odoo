/** @odoo-module */

import { useOpenChat } from "@mail/new/common/open_chat_hook";

import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class HrEmployeeChat extends Component {
    setup() {
        super.setup();
        this.openChat = useOpenChat(this.props.record.resModel);
    }
}
HrEmployeeChat.props = {
    ...standardWidgetProps,
};
HrEmployeeChat.template = "hr.OpenChat";

registry.category("view_widgets").add("hr_employee_chat", HrEmployeeChat);
