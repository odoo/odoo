import { Component, props, t, xml } from "@odoo/owl";
import { resolveBuilderLevel, useBuilderComponent } from "../utils";
import { BuilderComponent } from "./builder_component";
import { useSubEnv } from "@web/owl2/utils";

export class BuilderContext extends Component {
    static template = xml`
        <BuilderComponent>
            <t t-call-slot="default"/>
        </BuilderComponent>
    `;

    props = props({
        // basicContainerBuilderComponentProps (converted inline)
        applyTo: t.string().optional(),
        preview: t.boolean().optional(),
        inheritedActions: t.array(t.string()).optional(),

        action: t.string().optional(),
        actionParam: t.any().optional(),

        // Shorthand actions.
        styleAction: t.any().optional(),

        slots: t.object().optional(),
        level: t.boolean().optional()
    })

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
