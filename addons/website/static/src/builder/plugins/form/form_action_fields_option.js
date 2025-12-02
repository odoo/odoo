import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/utils";

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
        onWillStart(this.getFormInfo.bind(this));
        onWillUpdateProps(this.getFormInfo.bind(this));
    }
    async getFormInfo(props = this.props) {
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
