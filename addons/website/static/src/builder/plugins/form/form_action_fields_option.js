import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { t, useProps } from "@odoo/owl";
import { useAsyncComputed } from "@web/core/utils/hooks";

export class FormActionFieldsOption extends BaseOptionComponent {
    static template = "website.s_website_form_form_action_fields_option";
    static dependencies = ["websiteFormOption"];

    props = useProps({
        activeForm: t.object().optional(),
    });

    setup() {
        super.setup();

        this.prepareFormModel = this.dependencies.websiteFormOption.prepareFormModel;
        this.formInfo = useAsyncComputed(async () => {
            const { activeForm } = this.props;
            const el = this.env.getEditingElement();
            const formInfo = await this.prepareFormModel(el, activeForm);
            return {
                fields: [],
                formFields: [],
                successPage: undefined,
                ...formInfo,
            };
        });
    }
}
