/**@odoo-module */

import { fieldVisualFeedback } from "@web/fields/field";

const { Component, xml } = owl;

export class FormLabel extends Component {
    get className() {
        const { invalid, empty } = fieldVisualFeedback(this.props.record, this.props.fieldName);
        const classes = this.props.className ? [this.props.className] : [];
        if (invalid) {
            classes.push("o_field_invalid");
        }
        if (empty) {
            classes.push("o_form_label_empty");
        }
        return classes.join(" ");
    }
}
FormLabel.template = xml`
  <label class="o_form_label" t-att-for="props.id" t-att-class="className">
    <t t-esc="props.string" />
  </label>
`;
