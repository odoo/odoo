import { Component, onError, xml } from "@odoo/owl";

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
    static props = {
        env: { optional: false, type: Object },
        slots: { optional: true, type: Object },
    };
    setup() {
        this.__owl__.childEnv = this.props.env;
    }
}
