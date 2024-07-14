/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";

class OpenStudioWidget extends Component {
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.studio = useService("studio");
        this.ui = useService("ui");
    }
    async onClick() {
        this.ui.block();
        const action = await this.orm.call(
            "worksheet.template",
            "get_x_model_form_action",
            [this.props.record.resId]
        );
        await this.action.doAction(action);
        await this.studio.open();
        await this.studio.ready;
        this.ui.unblock();
    }
}

OpenStudioWidget.template = "worksheet.OpenStudioWidget";
OpenStudioWidget.props = {
    ...standardWidgetProps,
};

export const openStudioWidget = {
    component: OpenStudioWidget,
};
registry.category("view_widgets").add("open_studio_button", openStudioWidget);
