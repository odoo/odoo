import { Component, onError, useProps, xml } from "@odoo/owl";

export class ErrorHandler extends Component {
    static template = xml`<t t-call-slot="default" />`;
    props = useProps(["onError", "slots"]);
    setup() {
        onError((error) => {
            this.props.onError(error);
        });
    }
}
