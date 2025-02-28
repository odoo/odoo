import { Form } from "@website/snippets/s_website_form/form";
import { patch } from "@web/core/utils/patch";

patch(Form.prototype, {
    /**
     * @override
     */
    send() {
        // If the form is a signup form, we don't want to send the model_name
        // to ensure the signup controller is called correctly.
        if (this.el.classList.contains("oe_signup_form")) {
            this.el.dataset.model_name = "";
        }
        super.send();
    },
});
