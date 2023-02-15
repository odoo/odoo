/** @odoo-module **/

import { registry } from '@web/core/registry';
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

const { Component } = owl;

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
ColorsResetButton.extractProps = ({ attrs }) => {
    // Note: `options` should have `default_colors`. It's specified when using the widget.
    return attrs.options;
};

registry.category('view_widgets').add('colors_reset_button', ColorsResetButton);
