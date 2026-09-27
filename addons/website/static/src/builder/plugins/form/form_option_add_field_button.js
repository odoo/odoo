import { useOperation } from "@html_builder/core/operation_plugin";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useProps, t } from "@odoo/owl";

export class FormOptionAddFieldButton extends BaseOptionComponent {
    static template = "website.s_website_form_form_option_add_field_button";
    props = useProps({
        addField: t.function(),
        tooltip: t.string(),
    });

    setup() {
        this.callOperation = useOperation();
    }

    addField() {
        this.callOperation(() => {
            this.props.addField(this.env.getEditingElement());
        });
    }
}
