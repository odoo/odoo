import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component, t, useProps } from "@odoo/owl";

export class ColorsResetButton extends Component {
    static template = `im_livechat.ColorsResetButton`;
    props = useProps({
        ...standardWidgetProps,
        default_colors: t.object(),
    });

    onColorsResetButtonClick() {
        this.props.record.update(this.props.default_colors);
    }
}

export const colorsResetButton = {
    component: ColorsResetButton,
    extractProps: ({ options }) => ({
        // Note: `options` should have `default_colors`. It's specified when using the widget.
        default_colors: options.default_colors,
    }),
};
registry.category("view_widgets").add("colors_reset_button", colorsResetButton);
