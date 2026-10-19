import { Component, signal, t, useProps } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useVisibilityObserver,
    useApplyVisibility,
    useSelectableComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";

export class BuilderButtonGroup extends Component {
    static components = { BuilderComponent };
    static template = "html_builder.BuilderButtonGroup";

    props = useProps({
        ...basicContainerBuilderComponentProps,
        slots: t.object().optional(),
    });

    rootRef = signal.ref();

    setup() {
        useVisibilityObserver(this.rootRef, useApplyVisibility(this.rootRef));

        useSelectableComponent(this.props);
    }
}
