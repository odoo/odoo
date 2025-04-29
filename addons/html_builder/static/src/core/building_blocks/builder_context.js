import { Component, xml } from "@odoo/owl";
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
    };
    static components = {
        BuilderComponent,
    };

    setup() {
        useBuilderComponent();
    }
}
