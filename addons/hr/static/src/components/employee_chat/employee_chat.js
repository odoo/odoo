/** @odoo-module */

import { registry } from '@web/core/registry';
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { useOpenChat } from "@mail/new/web/open_chat_hook";

const { Component } = owl;

export class HrEmployeeChat extends Component {
    setup() {
        super.setup();
        this.openChat = useOpenChat(this.props.record.resModel);
    }
}
HrEmployeeChat.props = {
    ...standardWidgetProps,
};
HrEmployeeChat.template = 'hr.OpenChat';

export const hrEmployeeChat = {
    component: HrEmployeeChat,
};
registry.category("view_widgets").add("hr_employee_chat", hrEmployeeChat);
