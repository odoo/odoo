import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { getModelName, getParsedDataFor } from "./utils";
import { FormActionFieldsOption } from "./form_action_fields_option";
import { session } from "@web/session";

export class FormOption extends BaseOptionComponent {
    static template = "website.s_website_form_form_option";
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
        // Get the email_to value from the data-for attribute if it exists. We
        // use it if there is no value on the email_to input.
        const formId = el.id;
        const dataForValues = getParsedDataFor(formId, el.ownerDocument);
        if (dataForValues) {
            this.dataForEmailTo = dataForValues["email_to"];
        }
        this.state = useDomState(async (el) => {
            const modelName = getModelName(el);

            // Hide change form parameters option for forms e.g. User should not
            // be enable to change existing job application form to opportunity
            // form in 'Apply job' page.
            this.modelCantChange = !!el.getAttribute("hide-change-model");

            // Get list of website_form compatible models.
            const models = await this.props.fetchModels(el);
            const activeForm = models.find((m) => m.model === modelName);

            // If the form has no model it means a new snippet has been dropped.
            // Apply the default model selected in willStart on it.
            if (!el.dataset.model_name) {
                const formInfo = await this.props.prepareFormModel(el, activeForm);
                this.props.applyFormModel(el, activeForm, activeForm.id, formInfo);
            }
            return {
                models,
                activeForm,
            };
        });
    }
}
