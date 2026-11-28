import { Component, t } from "@odoo/owl";
import { displayValue } from "./display_value";
import { useField } from "./field";

/**
 * The value of a field that has no component yet, as readonly text.
 */
export class FallbackField extends Component {
    static template = "web.next.FallbackField";

    field = useField(t.any());

    text() {
        return displayValue(this.field.value(), this.field.node.field);
    }
}
