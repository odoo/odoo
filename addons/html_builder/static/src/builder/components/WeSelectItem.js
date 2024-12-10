import { Component, onMounted, useRef } from "@odoo/owl";
import {
    clickableWeWidgetProps,
    useClickableWeWidget,
    WeComponent,
    useDependecyDefinition,
} from "../builder_helpers";
import { useBus } from "@web/core/utils/hooks";

export class WeSelectItem extends Component {
    static template = "html_builder.WeSelectItem";
    static props = {
        ...clickableWeWidgetProps,
        id: { type: String, optional: true },
        title: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static components = { WeComponent };

    setup() {
        const item = useRef("item");
        const { state, call, isActive } = useClickableWeWidget();
        if (this.props.id) {
            useDependecyDefinition({ id: this.props.id, isActive });
        }

        const setSelectLabel = () => {
            if (isActive()) {
                this.env.weSetSelectLabel?.(item.el.innerHTML);
            }
        };
        useBus(this.env.editorBus, "STEP_ADDED", (ev) => {
            if (ev.detail.isPreviewing) {
                return;
            }
            return setSelectLabel();
        });
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
