import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { Component } from "@odoo/owl";

export class HrEmployeeChat extends Component {
    static props = {
        ...standardWidgetProps,
    };
    static template = "hr.OpenChat";

    setup() {
        super.setup();
        this.openChat = useOpenChat(this.props.record.resModel);
    }
}

export const hrEmployeeChat = {
    component: HrEmployeeChat,
};
registry.category("view_widgets").add("hr_employee_chat", hrEmployeeChat);
