import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component, useState } from "@odoo/owl";

export class MailingPreviewDisplayModeToggle extends Component {
    static template = "mass_mailing.MailingPreviewModeToggle";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.state = useState(this.env.displayState);
    }

    onTogglePreviewMode(isMobileMode) {
        this.state.isMobileMode = isMobileMode;
    }
}

export const mailingPreviewDisplayModeToggle = {
    component: MailingPreviewDisplayModeToggle,
};

registry
    .category("view_widgets")
    .add("mailing_preview_display_mode_toggle", mailingPreviewDisplayModeToggle);
