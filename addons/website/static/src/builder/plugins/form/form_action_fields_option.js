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
            shouldShowDropdown: {},
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
        for (const field of this.state.formInfo.fields) {
            if (field.type === "many2one" && field.required) {
                const recordsLength = field.records.length;
                this.state.shouldShowDropdown[field.name] = recordsLength > 0;
                const hiddenField = el.querySelector(
                    `.s_website_form_dnone input[name="${field.name}"]`
                )?.value;
                if (!hiddenField && recordsLength > 0) {
                    this.dependencies.websiteFormOption.addHiddenField(
                        el,
                        field.records[0].id,
                        field.name
                    );
                }
            } else {
                this.state.shouldShowDropdown[field.name] = true;
            }
        }
    }
}
