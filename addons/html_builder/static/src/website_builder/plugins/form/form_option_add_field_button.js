import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class FormOptionAddFieldButton extends BaseOptionComponent {
    // TODO create +Field template
    static template = "html_builder.website.s_website_form_form_option_add_field_button";
    static props = {
        addField: Function,
        tooltip: String,
    };
    setup() {
        super.setup();
        this.domState = useDomState((el) => ({
            el,
        }));
    }
}
