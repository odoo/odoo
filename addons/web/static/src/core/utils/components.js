/** @odoo-module **/

import { Component, onError, xml, useChildSubEnv } from "@odoo/owl";

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
        env: {
            type: Object,
            optional: true,
        },
        replace: {
            type: Boolean,
            optional: true,
        },
        slots: {
            type: Object,
            optional: true,
        },
    };
    setup() {
        if (this.props.replace) {
            this.__owl__.childEnv = this.props.env;
        } else {
            useChildSubEnv(this.props.env);
        }
    }
}
