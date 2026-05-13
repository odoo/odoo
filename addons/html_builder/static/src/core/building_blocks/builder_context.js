import { Component, xml } from "@odoo/owl";
import { basicContainerBuilderComponentProps, resolveBuilderLevel, useBuilderComponent } from "../utils";
import { BuilderComponent } from "./builder_component";
import { useSubEnv } from "@web/owl2/utils";

export class BuilderContext extends Component {
    static template = xml`
        <BuilderComponent>
            <t t-call-slot="default"/>
        </BuilderComponent>
    `;
    static props = {
        ...basicContainerBuilderComponentProps,
        slots: { type: Object },
        level: { type: Boolean, optional: true },
    };
    static components = {
        BuilderComponent,
    };

    setup() {
        useBuilderComponent();
        useSubEnv({
            builderLevel: resolveBuilderLevel(this.env, this.props.level),
        });
    }
}
