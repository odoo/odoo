import { Component } from "@odoo/owl";
import {
    useVisibilityObserver,
    useApplyVisibility,
    basicContainerBuilderComponentProps,
    useBuilderComponent,
} from "./utils";
import { BuilderComponent } from "./builder_component";

export class BuilderRow extends Component {
    static template = "html_builder.BuilderRow";
    static components = { BuilderComponent };
    static props = {
        ...basicContainerBuilderComponentProps,
        label: String,
        tooltip: { type: String, optional: true },
        slots: { type: Object, optional: true },
        level: { type: Number, optional: true },
    };

    setup() {
        useBuilderComponent();
        useVisibilityObserver("content", useApplyVisibility("root"));
    }

    getLevelClass() {
        return this.props.level ? `o_we_sublevel_${this.props.level}` : "";
    }
}
