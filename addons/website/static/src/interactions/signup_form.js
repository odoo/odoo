import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { parseDate, parseDateTime, serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { Interaction } from "@web/public/interaction";
import { Form } from "@website/snippets/s_website_form/form";

/**
 * The signup form is a form snippet (see the `website.signup_form` template), so
 * that its fields have the behaviors they have in the other form snippets.
 * Unlike them, it is submitted by the browser to `/web/signup`: it is only
 * checked before being submitted, not sent by the form interaction.
 */
export class SignupForm extends Form {
    static selector = ".s_website_form form.oe_signup_form";
    dynamicContent = {
        ...this.dynamicContent,
        ".s_website_form_send, .o_website_form_send": {},
        _root: {
            "t-on-submit.capture": this.onSubmit,
            "t-att-novalidate": () => true,
        },
        // The form builder does not keep these attributes of the standard
        // fields when rendering them again, and the password policy depends on
        // the request: they are set here rather than saved with the form.
        "input[name='name']": {
            "t-att-autocomplete": () => "name",
        },
        "input[name='login']": {
            "t-att-autocomplete": () => "username",
            "t-att-autocapitalize": () => "off",
        },
        "input[name='password']": {
            "t-att-minlength": () => this.passwordMinLength ?? Interaction.INITIAL_VALUE,
        },
    };

    setup() {
        super.setup();
        const passwordEl = this.el.querySelector("input[name='password']");
        const policyMinLength = parseInt(
            document.querySelector(`[data-for='${this.el.id}']`)?.dataset.passwordMinlength
        );
        if (passwordEl && policyMinLength > passwordEl.minLength) {
            this.passwordMinLength = policyMinLength;
        }
    }

    start() {
        super.start();
        // The password strength meter of `auth_password_policy_signup`.
        const passwordLabelEl = this.el.querySelector(
            ".s_website_form_field:has(input[name='password']) .s_website_form_label"
        );
        if (passwordLabelEl && registry.category("public_components").contains("password_meter")) {
            const meterEl = document.createElement("owl-component");
            meterEl.setAttribute("name", "password_meter");
            meterEl.setAttribute(
                "props",
                JSON.stringify({ selector: `#${this.el.id} input[name=password]` })
            );
            this.insert(meterEl, passwordLabelEl, "afterend");
        }
        this.el.querySelector("input[name='name']")?.focus();
    }

    /**
     * Checks the form before it is submitted, and prevents submission if there
     * are errors. The fields are checked as in the other form snippets.
     *
     * @param {SubmitEvent} ev
     */
    onSubmit(ev) {
        this.el.querySelector("#s_website_form_result")?.replaceChildren();
        this.removeErrorMessages();
        if (!this.checkErrorFields({})) {
            this.updateStatus("error", _t("Please fill in the form correctly."));
            ev.preventDefault();
            ev.stopImmediatePropagation();
            return;
        }
        for (const dateEl of this.el.querySelectorAll(
            ".s_website_form_field:not(.s_website_form_custom) :is(.s_website_form_date, .s_website_form_datetime)"
        )) {
            const inputEl = dateEl.querySelector("input");
            if (inputEl.value) {
                inputEl.value = dateEl.matches(".s_website_form_date")
                    ? serializeDate(parseDate(inputEl.value))
                    : serializeDateTime(parseDateTime(inputEl.value));
            }
        }
    }
}

registry.category("public.interactions").add("website.signup_form", SignupForm);
