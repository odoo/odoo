import { Component } from "@odoo/owl";
import { clickableWeWidgetProps, useClickableWeWidget, WeComponent } from "../builder_helpers";

export class WeButton extends Component {
    static template = "html_builder.WeButton";
    static components = { WeComponent };
    static props = {
        ...clickableWeWidgetProps,

        title: { type: String, optional: true },
        label: { type: String, optional: true },
        iconImg: { type: String, optional: true },
        iconImgAlt: { type: String, optional: true },
        icon: { type: String, optional: true },

        slots: { type: Object, optional: true },
    };

    setup() {
        const { state, call } = useClickableWeWidget();
        this.state = state;
        this.onClick = call.commit;
        this.onMouseenter = call.preview;
        this.onMouseleave = call.revert;
    }

    get className() {
        if (!this.props.icon) {
            return "";
        }
        if (this.props.icon.startsWith("fa-")) {
            return `fa fa-fw ${this.props.icon}`;
        } else if (this.props.icon.startsWith("oi-")) {
            return `oi oi-fw ${this.props.icon}`;
        }
        return "";
    }
}
