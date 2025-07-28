import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { getModelName, getParsedDataFor } from "./utils";
import { FormActionFieldsOption } from "./form_action_fields_option";
import { session } from "@web/session";
import { selectElements } from "@html_editor/utils/dom_traversal";

export class FormOption extends BaseOptionComponent {
    static template = "website.s_website_form_form_option";
    static dependencies = ["websiteFormOption"];
    static selector = ".s_website_form";
    static applyTo = "form";
    static components = { FormActionFieldsOption };
    static cleanForSave(el, { services }) {
        for (const sigEl of el.querySelectorAll("input[name=website_form_signature]")) {
            sigEl.remove();
        }

        for (const formEl of selectElements(el, ".s_website_form form[data-model_name]")) {
            const model = formEl.dataset.model_name;
            const fields = [
                ...formEl.querySelectorAll(
                    ".s_website_form_field:not(.s_website_form_custom) .s_website_form_input"
                ),
            ].map((el) => el.name);
            if (fields.length) {
                services.orm.call("ir.model.fields", "formbuilder_whitelist", [
                    model,
                    [...new Set(fields)],
                ]);
            }
        }
    }

    setup() {
        super.setup();
        const { prepareFormModel, applyFormModel, fetchModels } =
            this.dependencies.websiteFormOption;
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
            const models = await fetchModels(el);
            const activeForm = models.find((m) => m.model === modelName);

            // If the form has no model it means a new snippet has been dropped.
            // Apply the default model selected in willStart on it.
            if (!el.dataset.model_name) {
                const formInfo = await prepareFormModel(el, activeForm);
                applyFormModel(el, activeForm, activeForm.id, formInfo);
            }
            return {
                models,
                activeForm,
            };
        });
    }
}
