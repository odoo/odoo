import { Component } from "@odoo/owl";
import { clickableWeWidgetProps, useClickableWeWidget } from "../builder_helpers";

export class WeButton extends Component {
    static template = "html_builder.WeButton";
    static props = {
        ...clickableWeWidgetProps,

        title: { type: String, optional: true },
        label: { type: String, optional: true },
        iconImg: { type: String, optional: true },
        iconImgAlt: { type: String, optional: true },

        slots: { type: Object, optional: true },
    };

    setup() {
        const { state, call } = useClickableWeWidget();
        this.state = state;
        this.onClick = call.commit;
        this.onMouseenter = call.preview;
        this.onMouseleave = call.revert;
    }
}
