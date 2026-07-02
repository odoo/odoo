import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useClickableBuilderComponent, clickableBuilderComponentProps } from "../utils";
import { BuilderComponent } from "./builder_component";

export class BuilderDropdownItem extends Component {
    static template = "html_builder.BuilderDropdownItem";

    static props = {
        ...clickableBuilderComponentProps,
        class: { type: [String, Object], optional: true },
        slots: { type: Object, optional: true },
    };

    static defaultProps = {
        class: "",
    };

    static components = { BuilderComponent, DropdownItem };

    setup() {
        const { operation } = useClickableBuilderComponent();
        this.operation = operation;
    }

    onSelected() {
        this.operation.commit();
    }
}
