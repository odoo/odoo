import { useOperation } from "@html_builder/core/operation_plugin";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class FormOptionAddFieldButton extends BaseOptionComponent {
    static template = "website.s_website_form_form_option_add_field_button";
    static props = {
        addField: Function,
        tooltip: String,
    };

    setup() {
        this.callOperation = useOperation();
    }

    addField() {
        this.callOperation(() => {
            this.props.addField(this.env.getEditingElement());
        });
    }
}
