import { Component } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useVisibilityObserver,
    useApplyVisibility,
    useSelectableComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";

export class BuilderButtonGroup extends Component {
    static template = "html_builder.BuilderButtonGroup";
    static props = {
        ...basicContainerBuilderComponentProps,
        slots: { type: Object, optional: true },
    };
    static components = { BuilderComponent };

    setup() {
        useVisibilityObserver("root", useApplyVisibility("root"));

        useSelectableComponent(this.props.id);
    }
}
