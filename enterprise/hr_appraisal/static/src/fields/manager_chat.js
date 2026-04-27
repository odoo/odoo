/** @odoo-module */

import { registry } from '@web/core/registry';
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { Component } from "@odoo/owl";

export class AppraisalManagerChat extends Component {
    static template = "hr_appraisal.ManagerChat";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        super.setup();
        this.openChat = useOpenChat('hr.employee');
    }
}

export const appraisalManagerChat = {
    component: AppraisalManagerChat,
};
registry.category("view_widgets").add("appraisal_manager_chat", appraisalManagerChat);
