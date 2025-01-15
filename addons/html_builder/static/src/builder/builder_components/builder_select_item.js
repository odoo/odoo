import { Component, useRef } from "@odoo/owl";
import {
    clickableBuilderComponentProps,
    BuilderComponent,
    useSelectableItemComponent,
} from "./utils";

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

        const { state, operation } = useSelectableItemComponent(this.props.id, {
            getLabel: () => item.el?.innerHTML || "",
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
