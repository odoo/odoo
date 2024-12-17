import { Component, onMounted, onWillDestroy, useRef } from "@odoo/owl";
import {
    clickableWeWidgetProps,
    useClickableWeWidget,
    useDependecyDefinition,
    WeComponent,
} from "../builder_helpers";

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
        if (!this.env.weSelectContext) {
            throw new Error("WeSelectItem must be used inside a WeSelect component.");
        }
        const item = useRef("item");
        const { state, operation, isActive, getActions, priority } = useClickableWeWidget();
        if (this.props.id) {
            useDependecyDefinition({ id: this.props.id, isActive, getActions });
        }

        const selectableItem = {
            isActive,
            priority,
            getLabel: () => item.el?.innerHTML || "",
        };

        this.env.weSelectContext.addSelectableItem?.(selectableItem);
        onMounted(this.env.weSelectContext.update);
        onWillDestroy(() => {
            this.env.weSelectContext.removeSelectableItem?.(selectableItem);
        });

        this.state = state;
        this.onClick = () => {
            operation.commit();
            this.env.weSelectContext.bus.trigger("select-item");
        };
        this.onMouseenter = operation.preview;
        this.onMouseleave = operation.revert;
    }
}
