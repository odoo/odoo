/** @odoo-module */

import { Component, useEffect } from "@odoo/owl";

export class Loader extends Component {
    static template = "point_of_sale.Loader";
    static props = { loader: { type: Object, shape: { isShown: Boolean } } };
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
