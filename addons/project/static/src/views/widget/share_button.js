
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";
import { PermissionPanel } from "../../components/permission_panel/permission_panel";


class ShareButtonWidget extends Component {
    static template = "share.Button";
    static props = {
        ...standardWidgetProps,
    };
    static components = {
        PermissionPanel,
    };
    static defaultProps = {
    };
}

export const shareButton = {
    component: ShareButtonWidget,
};

registry.category("view_widgets").add("project_share_button", shareButton);
