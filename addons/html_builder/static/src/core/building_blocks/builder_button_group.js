import { Component, signal } from "@odoo/owl";
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
    rootRef = signal.ref();

    setup() {
        useVisibilityObserver(this.rootRef, useApplyVisibility(this.rootRef));

        useSelectableComponent(this.props.id);
    }
}
