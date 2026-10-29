import { Component, Plugin, providePlugins, t, useConfig, useProps, xml } from "@odoo/owl";
import { basicContainerBuilderComponentProps, useBuilderComponent } from "../utils";
import { BuilderComponent } from "./builder_component";
import { useMaybePlugin } from "../hooks";

export class BuilderLevelPlugin extends Plugin {
    level = useConfig("level", t.number().optional(0));
}

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
        level: t.boolean().optional(false),
    });

    setup() {
        useBuilderComponent(this.props);

        // Without `level`, children inherit the parent's level plugin as is.
        if (this.props.level) {
            const parentLevel = useMaybePlugin(BuilderLevelPlugin)?.level ?? 0;
            providePlugins([BuilderLevelPlugin], { level: parentLevel + 1 });
        }
    }
}
