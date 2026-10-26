import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { _t } from "@web/core/l10n/translation";
import { Component, useProps } from "@odoo/owl";

// Extended by website_livechat to restore the linked website's colors
// instead, when the channel is following one - see colors_reset_button_patch.js.
export class ColorsResetButton extends Component {
    static template = `im_livechat.ColorsResetButton`;
    props = useProps(standardWidgetProps);

    get label() {
        return _t("Reset to default colors");
    }

    onClick() {
        // Plain client-side update, like any other field: stays part of the
        // form's normal dirty/Save/Cancel flow instead of writing to the
        // database immediately. default_colors is already on the record
        // (see im_livechat_channel.py), no round-trip needed.
        this.props.record.update(this.props.record.data.default_colors);
    }
}

export const colorsResetButton = {
    component: ColorsResetButton,
};
registry.category("view_widgets").add("colors_reset_button", colorsResetButton);
