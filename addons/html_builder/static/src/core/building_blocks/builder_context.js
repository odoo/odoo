import { Component, xml } from "@odoo/owl";
import { useSubEnv } from "@web/owl2/utils";
import { basicContainerBuilderComponentProps, useBuilderComponent } from "../utils";
import { BuilderComponent } from "./builder_component";

export class BuilderContext extends Component {
    static template = xml`
        <BuilderComponent>
            <t t-slot="default"/>
        </BuilderComponent>
    `;
    static props = {
        ...basicContainerBuilderComponentProps,
        slots: { type: Object },
        level: { type: Number, optional: true },
    };
    static components = {
        BuilderComponent,
    };

    setup() {
        useBuilderComponent();
        useSubEnv({
            builderLevel: this.props.level || 0,
        });
    }
}
