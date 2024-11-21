import { Component, onMounted, useRef } from "@odoo/owl";
import { clickableWeWidgetProps, useClickableWeWidget } from "../builder_helpers";

export class WeSelectItem extends Component {
    static template = "html_builder.WeSelectItem";
    static props = {
        ...clickableWeWidgetProps,
        title: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    setup() {
        const item = useRef("item");
        const { state, call, isActive } = useClickableWeWidget();

        const setSelectLabel = () => {
            if (isActive()) {
                this.env.weSetSelectLabel?.(item.el.innerHTML);
            }
        };
        onMounted(setSelectLabel);

        this.state = state;
        this.onClick = () => {
            call.commit();
            setSelectLabel();
            this.env.weSelectBus?.trigger("select-item");
        };
        this.onMouseenter = call.preview;
        this.onMouseleave = call.revert;
    }
}
