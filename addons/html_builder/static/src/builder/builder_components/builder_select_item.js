import { Component, onMounted, onWillDestroy, useRef } from "@odoo/owl";
import {
    clickableBuilderComponentProps,
    defaultBuilderComponentProps,
    useClickableBuilderComponent,
    useDependecyDefinition,
    BuilderComponent,
} from "../builder_helpers";

export class BuilderSelectItem extends Component {
    static template = "html_builder.BuilderSelectItem";
    static props = {
        ...clickableBuilderComponentProps,
        id: { type: String, optional: true },
        title: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = defaultBuilderComponentProps;
    static components = { BuilderComponent };

    setup() {
        if (!this.env.BuilderSelectContext) {
            throw new Error("BuilderSelectItem must be used inside a BuilderSelect component.");
        }
        const item = useRef("item");
        const { state, operation, isActive, getActions, priority } = useClickableBuilderComponent();
        if (this.props.id) {
            useDependecyDefinition({ id: this.props.id, isActive, getActions });
        }

        const selectableItem = {
            isActive,
            priority,
            getLabel: () => item.el?.innerHTML || "",
        };

        this.env.BuilderSelectContext.addSelectableItem?.(selectableItem);
        onMounted(this.env.BuilderSelectContext.update);
        onWillDestroy(() => {
            this.env.BuilderSelectContext.removeSelectableItem?.(selectableItem);
        });

        this.state = state;
        this.onClick = () => {
            operation.commit();
            this.env.BuilderSelectContext.bus.trigger("select-item");
        };
        this.onMouseenter = operation.preview;
        this.onMouseleave = operation.revert;
    }
}
