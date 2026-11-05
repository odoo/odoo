import { patch } from "@web/core/utils/patch";
import wUtils from "@website/js/utils";
import { Form } from "@website/snippets/s_website_form/form";

patch(Form.prototype, {
    /**
     * @override
     */
    prefillValues() {
        super.prefillValues();
        if (this.el.dataset.model_name !== "crm.lead") {
            return;
        }
        // The `subject` value targets the email form, a lead keeps its subject in `name`.
        const dataForValues = wUtils.getParsedDataFor(this.el.id, document);
        const nameEl = this.el.querySelector("[name='name']");
        if (nameEl && dataForValues?.subject && !dataForValues.name) {
            this.initialValues.set(nameEl, nameEl.getAttribute("value"));
            nameEl.value = dataForValues.subject;
        }
    },
});
