// @ts-check

/** @module @web/core/utils/components - ErrorHandler component that catches child rendering errors */

import { Component, onError, xml } from "@odoo/owl";

export class ErrorHandler extends Component {
    static template = xml`<t t-slot="default" />`;
    static props = ["onError", "slots"];
    /** Register an error boundary that delegates to the parent's onError callback. */
    setup() {
        onError((/** @type {Error} */ error) => {
            this.props.onError(error);
        });
    }
}
