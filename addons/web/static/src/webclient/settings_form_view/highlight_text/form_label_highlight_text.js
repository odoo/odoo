/** @odoo-module **/
import { FormLabel } from "@web/views/form/form_label";
import { HighlightText } from "./highlight_text";

export class FormLabelHighlightText extends FormLabel {
    setup() {
        super.setup();
    }
    get labelClasses() {
        if (this.props.labelClasses) {
            return this.props.labelClasses;
        }
        return super.labelClasses;
    }
}

FormLabelHighlightText.template = "web.FormLabelHighlightText";
FormLabelHighlightText.components = { HighlightText };
