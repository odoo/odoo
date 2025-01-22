import { Component, onWillDestroy, xml } from "@odoo/owl";
import { useDependencies, useDomState } from "./utils";
import { useBus } from "@web/core/utils/hooks";

export class BuilderComponent extends Component {
    static template = xml`<t t-if="this.state.isVisible"><t t-slot="default"/></t>`;
    static props = {
        dependencies: { type: [String, { type: Array, element: String }], optional: true },
        slots: { type: Object },
    };

    setup() {
        const isDependenciesVisible = useDependencies(this.props.dependencies);
        const isVisible = () =>
            !!this.env.getEditingElement() && (!this.props.dependencies || isDependenciesVisible());
        this.state = useDomState(() => ({
            isVisible: isVisible(),
        }));
        useBus(this.env.dependencyManager, "dependency-updated", () => {
            this.state.isVisible = isVisible();
        });
        if (this.props.dependencies?.length) {
            const listener = () => {
                this.state.isVisible = isVisible();
            };
            this.env.dependencyManager.addEventListener("dependency-updated", listener);
            onWillDestroy(() => {
                this.env.dependencyManager.removeEventListener("dependency-updated", listener);
            });
        }
    }
}
