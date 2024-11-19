import { Component } from "@odoo/owl";
import { clickableWeWidgetProps, useClickableWeWidget } from "../builder_helpers";

export class WeSelectItem extends Component {
    static template = "html_builder.WeSelectItem";
    static props = {
        ...clickableWeWidgetProps,
        title: { type: String, optional: true },
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
