import options from "@web_editor/js/editor/snippets.options";

options.registry.WebsiteFormEditor.include({
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (widgetName === "signup_form_opt") {
            // To hide onSuccess we-button in signup form
            return !this.$target[0].classList.contains("oe_signup_form");
        }
        return this._super(...arguments);
    },
});

options.registry.WebsiteFieldEditor.include({
    /**
     * @override
     */
    _getActiveField() {
        const res = this._super(...arguments);
        // The "Confirm Password" field in the signup form is a custom field.
        // When calling the `_getCustomField` method, it pass name as its the
        // label content "Confirm Password" to identify the field. For the signup form,
        // the field's name attribute must be set to "confirm_password."
        if (
            this.formEl.classList.contains("oe_signup_form") &&
            res?.name === "Confirm Password"
        ) {
            res.name = "confirm_password";
        }
        return res;
    },
});
