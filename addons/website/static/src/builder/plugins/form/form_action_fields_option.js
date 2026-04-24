import { useState } from "@web/owl2/utils";
import { onWillStart, onWillUpdateProps } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";

export class FormActionFieldsOption extends BaseOptionComponent {
    static template = "website.s_website_form_form_action_fields_option";
    static dependencies = ["websiteFormOption"];
    static props = {
        activeForm: { type: Object, optional: true },
    };

    setup() {
        super.setup();
        this.prepareFormModel = this.dependencies.websiteFormOption.prepareFormModel;
        this.state = useState({
            formInfo: {
                fields: [],
            },
        });
        onWillStart(() => this.getFormInfo(this.props));
        onWillUpdateProps((np) => this.getFormInfo(np));
    }
    async getFormInfo(props) {
        const el = this.env.getEditingElement();
        const formInfo = await this.prepareFormModel(el, props.activeForm);
        Object.assign(
            this.state.formInfo,
            {
                fields: [],
                formFields: [],
                successPage: undefined,
            },
            formInfo
        );
    }
}
