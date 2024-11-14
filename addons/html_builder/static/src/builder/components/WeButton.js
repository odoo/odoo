import { Component } from "@odoo/owl";
import { basicContainerWeWidgetProps, useClickableWeWidget } from "../builder_helpers";

export class WeButton extends Component {
    static template = "html_builder.WeButton";
    static props = {
        ...basicContainerWeWidgetProps,

        title: { type: String, optional: true },
        label: { type: String, optional: true },
        iconImg: { type: String, optional: true },
        iconImgAlt: { type: String, optional: true },

        actionValue: {
            type: [Boolean, String, Number, { type: Array, element: [Boolean, String, Number] }],
            optional: true,
        },

        // Shorthand actions values.
        classActionValue: { type: [String, Array], optional: true },
        attributeActionValue: { type: [String, Array], optional: true },
        dataAttributeActionValue: { type: [String, Array], optional: true },
        styleActionValue: { type: [String, Array], optional: true },

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
