import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { getParsedDataFor } from "./utils";
import { FormActionFieldsOption } from "./form_action_fields_option";
import { session } from "@web/session";

export class FormOption extends BaseOptionComponent {
    static template = "html_builder.website.s_website_form_form_option";
    static props = {
        modelName: String,
        fetchModels: Function,
        prepareFormModel: Function,
        fetchFieldRecords: Function,
        applyFormModel: Function,
    };
    static components = { FormActionFieldsOption };

    setup() {
        super.setup();
        this.hasRecaptchaKey = !!session.recaptcha_public_key;

        // Get potential message
        const el = this.env.getEditingElement();
        this.messageEl = el.parentElement.querySelector(".s_website_form_end_message");
        this.showEndMessage = false;
        this.state = useState({
            activeForm: {},
        });
        // Get the email_to value from the data-for attribute if it exists. We
        // use it if there is no value on the email_to input.
        const formId = el.id;
        const dataForValues = getParsedDataFor(formId, el.ownerDocument);
        if (dataForValues) {
            this.dataForEmailTo = dataForValues["email_to"];
        }
        onWillStart(async () => this.handleProps(this.props));
        onWillUpdateProps(async (props) => this.handleProps(props));
    }
    async handleProps(props) {
        const el = this.env.getEditingElement();
        // Hide change form parameters option for forms
        // e.g. User should not be enable to change existing job application form
        // to opportunity form in 'Apply job' page.
        this.modelCantChange = !!el.getAttribute("hide-change-model");

        // Get list of website_form compatible models.
        this.models = await props.fetchModels(el);
        this.state.activeForm = this.models.find((m) => m.model === props.modelName);

        // If the form has no model it means a new snippet has been dropped.
        // Apply the default model selected in willStart on it.
        if (!el.dataset.model_name) {
            const formInfo = await props.prepareFormModel(el, this.state.activeForm);
            props.applyFormModel(el, this.state.activeForm, this.state.activeForm.id, formInfo);
        }
    }
}
