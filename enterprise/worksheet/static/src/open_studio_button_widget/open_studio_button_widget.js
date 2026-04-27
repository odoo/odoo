/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";

class OpenStudioWidget extends Component {
    static template = "worksheet.OpenStudioWidget";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.studio = useService("studio");
        this.ui = useService("ui");
    }
    async onClick() {
        if (!this.props.record.resId) {
            if (!(await this.props.record.save())) {
                return;
            }
        }
        const action = await this.orm.call(
            "worksheet.template",
            "get_x_model_form_action",
            [this.props.record.resId]
        );
        await this.action.doAction(action);
        this.ui.block();
        await this.studio.open();
        await this.studio.ready;
        this.ui.unblock();
    }
}

export const openStudioWidget = {
    component: OpenStudioWidget,
};
registry.category("view_widgets").add("open_studio_button", openStudioWidget);
