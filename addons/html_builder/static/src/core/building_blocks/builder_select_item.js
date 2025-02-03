import { Component, onMounted, useRef } from "@odoo/owl";
import { clickableBuilderComponentProps, useSelectableItemComponent } from "./utils";
import { BuilderComponent } from "./builder_component";

export class BuilderSelectItem extends Component {
    static template = "html_builder.BuilderSelectItem";
    static props = {
        ...clickableBuilderComponentProps,
        id: { type: String, optional: true },
        title: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static components = { BuilderComponent };

    setup() {
        if (!this.env.selectableContext) {
            throw new Error("BuilderSelectItem must be used inside a BuilderSelect component.");
        }
        const item = useRef("item");
        let label = "";
        const getLabel = () => {
            // todo: it's not clear why the item.el?.innerHTML is not set at in
            // some cases. We fallback on a previously set value to circumvent
            // the problem, but it should be investigated.
            label = item.el?.innerHTML || label || "";
            return label;
        };

        onMounted(getLabel);

        const { state, operation } = useSelectableItemComponent(this.props.id, {
            getLabel,
        });
        this.state = state;
        this.onClick = () => {
            this.env.onSelectItem();
            operation.commit();
        };
        this.onMouseenter = operation.preview;
        this.onMouseleave = operation.revert;
    }
}
