import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { Component, t, useProps } from "@odoo/owl";

export class HrEmployeeChat extends Component {
    static template = "hr.OpenChat";

    props = useProps({
        ...standardWidgetProps,
        showLabel: t.boolean().optional(),
    });

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }
}

export const hrEmployeeChat = {
    component: HrEmployeeChat,
    extractProps({ options }) {
        return {
            showLabel: Boolean(options.show_label),
        };
    },
};

registry.category("view_widgets").add("hr_employee_chat", hrEmployeeChat);
