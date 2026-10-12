import { Component, onWillStart, t, useProps, xml } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";

/**
 * Utility component that loads an asset bundle before instanciating a component
 */
export class LazyComponent extends Component {
    static template = xml`<t t-component="this.Component" t-props="this.componentProps"/>`;
    props = useProps({
        Component: t.string(),
        bundle: t.string(),
        props: t.or([t.object(), t.function()]).optional(),
    });

    setup() {
        onWillStart(async () => {
            await loadBundle(this.props.bundle);
            this.Component = registry.category("lazy_components").get(this.props.Component);
        });
    }

    get componentProps() {
        return typeof this.props.props === "function" ? this.props.props() : this.props.props;
    }
}
