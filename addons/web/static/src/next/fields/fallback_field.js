import { Component, useProps } from "@odoo/owl";
import { displayValue } from "./display_value";
import { fieldProps } from "./field";

/**
 * The value of a field that has no component yet, as readonly text.
 */
export class FallbackField extends Component {
    static template = "web.next.FallbackField";

    props = useProps(fieldProps);

    get value() {
        return displayValue(this.props.record[this.props.name](), this.props.node.field);
    }
}
