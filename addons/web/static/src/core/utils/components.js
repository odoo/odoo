/** @odoo-module **/

import { Component, onError, xml, useSubEnv } from "@odoo/owl";

export class ErrorHandler extends Component {
    setup() {
        onError((error) => {
            this.props.onError(error);
        });
    }
}
ErrorHandler.template = xml`<t t-slot="default" />`;
ErrorHandler.props = ["onError", "slots"];

export class WithEnv extends Component {
    setup() {
        useSubEnv(this.props.env);
    }
}
WithEnv.template = xml`<t t-slot="default"/>`;
WithEnv.props = ["env", "slots"];
