/** @odoo-module */

import { registry } from '@web/core/registry';
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { Component } from "@odoo/owl";

export class AppraisalManagerChat extends Component {
    setup() {
        super.setup();
        this.openChat = useOpenChat('hr.employee');
    }
}
AppraisalManagerChat.props = {
    ...standardWidgetProps,
};
AppraisalManagerChat.template = 'hr_appraisal.ManagerChat';

export const appraisalManagerChat = {
    component: AppraisalManagerChat,
};
registry.category("view_widgets").add("appraisal_manager_chat", appraisalManagerChat);
