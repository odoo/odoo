import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { FormFieldOption } from "./form_field_option";

// TODO DUAU: check props here
export class FormFieldOptionRedraw extends BaseOptionComponent {
    static id = "form_field_option_redraw";
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

registry.category("builder-options").add(FormFieldOptionRedraw.id, FormFieldOptionRedraw);
