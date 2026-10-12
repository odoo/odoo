import { Component, t, useProps, xml } from "@odoo/owl";
import { basicContainerBuilderComponentProps, useBuilderComponent } from "../utils";
import { BuilderComponent } from "./builder_component";

export class BuilderContext extends Component {
    static components = { BuilderComponent };
    static template = xml`
        <BuilderComponent>
            <t t-call-slot="default"/>
        </BuilderComponent>
    `;

    props = useProps({
        ...basicContainerBuilderComponentProps,
        slots: t.object(),
    });

    setup() {
        useBuilderComponent(this.props);
    }
}
