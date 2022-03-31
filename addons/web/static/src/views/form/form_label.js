/**@odoo-module */
import { fieldVisualFeedback } from "@web/fields/field";

 
export class FormLabel extends owl.Component {

    get labelClasses() {
        const { invalid, empty } = fieldVisualFeedback(this.props.record, this.props.fieldName);
        return {
            "o_field_invalid": invalid,
            "o_form_label_empty" :empty,
        };
    }
}
FormLabel.template = owl.xml`
  <label class="o_form_label" t-att-for="props.id" t-att-class="labelClasses">
    <t t-esc="props.string" />
  </label>
`;
