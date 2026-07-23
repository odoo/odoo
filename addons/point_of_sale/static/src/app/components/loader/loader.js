import { Component, t, useApp, useEffect, useProps } from "@odoo/owl";
import { CriticalPOSError } from "./critical_pos_error/critical_pos_error";

export class Loader extends Component {
    static template = "point_of_sale.Loader";
    props = useProps({ loader: t.object({ isShown: t.boolean(), error: t.object() }) });
    static components = { CriticalPOSError };

    setup() {
        const app = useApp();
        useEffect(() => {
            if (!this.props.loader.isShown) {
                // Destroy the loader app after it has faded out
                setTimeout(() => app.destroy(), 1000);
            }
        });
    }
}
