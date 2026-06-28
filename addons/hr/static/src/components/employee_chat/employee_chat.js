import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { Component } from "@odoo/owl";

export class HrEmployeeChat extends Component {
    static props = { ...standardWidgetProps };
    static template = "hr.OpenChat";

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }
}

export const hrEmployeeChat = { component: HrEmployeeChat };
registry.category("view_widgets").add("hr_employee_chat", hrEmployeeChat);
