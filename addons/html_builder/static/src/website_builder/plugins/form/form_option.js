import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { getParsedDataFor } from "./utils";
import { FormActionFieldsOption } from "./form_action_fields_option";
import { session } from "@web/session";

export class FormOption extends BaseOptionComponent {
    static template = "html_builder.website.s_website_form_form_option";
    static props = {
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
        onWillStart(async () => {
            // Hide change form parameters option for forms
            // e.g. User should not be enable to change existing job application form
            // to opportunity form in 'Apply job' page.
            this.modelCantChange = !!el.getAttribute("hide-change-model");

            // Get list of website_form compatible models.
            this.models = await this.props.fetchModels();

            const targetModelName = el.dataset.model_name || "mail.mail";
            this.domState.activeForm = this.models.find((m) => m.model === targetModelName);

            // If the form has no model it means a new snippet has been dropped.
            // Apply the default model selected in willStart on it.
            if (!el.dataset.model_name) {
                const formInfo = await this.props.prepareFormModel(el, this.domState.activeForm);
                this.props.applyFormModel(
                    el,
                    this.domState.activeForm,
                    this.domState.activeForm.id,
                    formInfo
                );
            }
        });
        this.domState = useDomState((el) => {
            if (!this.models) {
                return {
                    activeForm: {},
                };
            }
            const targetModelName = el.dataset.model_name || "mail.mail";
            const activeForm = this.models.find((m) => m.model === targetModelName);
            return {
                activeForm,
            };
        });
        // Get the email_to value from the data-for attribute if it exists. We
        // use it if there is no value on the email_to input.
        const formId = el.id;
        const dataForValues = getParsedDataFor(formId, el.ownerDocument);
        if (dataForValues) {
            this.dataForEmailTo = dataForValues["email_to"];
        }
        this.defaultEmailToValue = "info@yourcompany.example.com";
    }
}
