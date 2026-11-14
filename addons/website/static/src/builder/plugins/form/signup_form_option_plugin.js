import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { FormFieldOption } from "./form_field_option";
import { FormOption } from "./form_option";
import { FormOptionPlugin } from "./form_option_plugin";

// The signup form is a form snippet on the `res.partner` model (see the
// `website.signup_form` template). Its standard fields, the ones required by the
// model, are handled by `auth_signup`.
const SIGNUP_FORM_SELECTOR = ".s_website_form form.oe_signup_form";
const SIGNUP_FIELDS_SELECTOR = `${SIGNUP_FORM_SELECTOR} .s_website_form_model_required`;

/**
 * Returns the standard fields of the signup form which are not `res.partner`
 * fields, so that the form builder can render them again (e.g. when changing
 * the position of the labels).
 *
 * @returns {Object}
 */
function getSignupFields() {
    return {
        login: { name: "login", string: _t("Email"), type: "email" },
        password: { name: "password", string: _t("Password"), type: "password" },
        confirm_password: {
            name: "confirm_password",
            string: _t("Confirm Password"),
            type: "password",
        },
    };
}

patch(FormOptionPlugin.prototype, {
    async loadFieldOptionData(fieldEl) {
        const data = await super.loadFieldOptionData(...arguments);
        if (fieldEl.closest(SIGNUP_FORM_SELECTOR)) {
            Object.assign(data.fields, getSignupFields());
        }
        return data;
    },
});

patch(FormOption.prototype, {
    get isSignupForm() {
        return this.env.getEditingElement().matches(SIGNUP_FORM_SELECTOR);
    },
});

patch(FormFieldOption.prototype, {
    get isSignupField() {
        return this.env.getEditingElement().matches(SIGNUP_FIELDS_SELECTOR);
    },
});
