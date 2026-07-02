import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class ImLivechatWidgetPreview extends Component {
    static template = "im_livechat.ImLivechatWidgetPreview";
    static props = standardWidgetProps;
}

registry.category("view_widgets").add("im_livechat_widget_preview", {
    component: ImLivechatWidgetPreview,
});
