/* @odoo-module */

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";

export class ColorsResetButton extends Component {
    onColorsResetButtonClick() {
        this.props.record.update(this.props.default_colors);
    }
}
ColorsResetButton.template = `im_livechat.ColorsResetButton`;
ColorsResetButton.props = {
    ...standardWidgetProps,
    default_colors: { type: Object },
};

export const colorsResetButton = {
    component: ColorsResetButton,
    extractProps: ({ options }) => ({
        // Note: `options` should have `default_colors`. It's specified when using the widget.
        default_colors: options.default_colors,
    }),
};
registry.category("view_widgets").add("colors_reset_button", colorsResetButton);
