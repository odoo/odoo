import { Component, onError, xml, useSubEnv } from "@odoo/owl";

export class ErrorHandler extends Component {
    static template = xml`<t t-slot="default" />`;
    static props = ["onError", "slots"];
    setup() {
        onError((error) => {
            this.props.onError(error);
        });
    }
}

export class WithEnv extends Component {
    static template = xml`<t t-slot="default"/>`;
    static props = ["env", "slots"];
    setup() {
        useSubEnv(this.props.env);
    }
}
