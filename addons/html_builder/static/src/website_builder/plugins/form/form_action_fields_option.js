import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class FormActionFieldsOption extends BaseOptionComponent {
    static template = "html_builder.website.s_website_form_form_action_fields_option";
    static props = {
        activeForm: Object,
        prepareFormModel: Function,
    };

    setup() {
        super.setup();
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
        const formInfo = await this.props.prepareFormModel(el, props.activeForm);
        Object.assign(this.state.formInfo, formInfo);
    }
}
