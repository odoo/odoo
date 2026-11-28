import { Component, onWillStart, t, useProps, xml } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";

/**
 * Utility component that loads an asset bundle before instanciating a component,
 * unless the component is already registered.
 */
export class LazyComponent extends Component {
    static template = xml`<t t-component="this.Component" t-props="this.componentProps"/>`;
    props = useProps({
        Component: t.string(),
        bundle: t.string(),
        props: t.or([t.object(), t.function()]).optional(),
    });

    setup() {
        const components = registry.category("lazy_components");
        this.Component = components.get(this.props.Component, null);
        if (!this.Component) {
            onWillStart(async () => {
                await loadBundle(this.props.bundle);
                this.Component = components.get(this.props.Component);
            });
        }
    }

    get componentProps() {
        return typeof this.props.props === "function" ? this.props.props() : this.props.props;
    }
}
