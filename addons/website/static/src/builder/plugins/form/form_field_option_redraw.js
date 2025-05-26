import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { FormFieldOption } from "./form_field_option";

export class FormFieldOptionRedraw extends BaseOptionComponent {
    static template = "website.s_website_form_field_option_redraw";
    static props = FormFieldOption.props;
    static components = { FormFieldOption };

    setup() {
        super.setup();
        this.count = 0;
        this.domState = useDomState((el) => {
            this.count++;
            return {
                redrawSequence: this.count++,
            };
        });
    }
}
