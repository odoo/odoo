import { Component, useEffect } from "@odoo/owl";
import { CriticalPOSError } from "./critical_pos_error/critical_pos_error";

export class Loader extends Component {
    static template = "point_of_sale.Loader";
    static props = { loader: { type: Object, shape: { isShown: Boolean, error: Object } } };
    static components = { CriticalPOSError };

    setup() {
        useEffect(
            (isShown) => {
                if (!isShown) {
                    // Destroy the loader app after it has faded out
                    setTimeout(() => {
                        this.__owl__.app.destroy();
                    }, 1000);
                }
            },
            () => [this.props.loader.isShown]
        );
    }
}
