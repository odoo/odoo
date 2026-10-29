import {
	Component,
	Plugin,
	providePlugins,
	t,
	usePlugin,
	useProps,
	xml,
	useConfig,
} from "@odoo/owl";
import {
	basicContainerBuilderComponentProps,
	useBuilderComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { useMaybePlugin } from "../hooks";

export class BuilderLevelPlugin extends Plugin {
	level = useConfig("level", t.number(0));
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

		const parentLevel = useMaybePlugin(BuilderLevelPlugin)?.level ?? 0;
		providePlugins([BuilderLevelPlugin], {
			level: parentLevel + Number(this.props.level),
		});

		this.builderLevel = usePlugin(BuilderLevelPlugin);
	}
}
