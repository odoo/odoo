import { registry } from "@web/core/registry";
import { parseDate, parseDateTime, serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { Form } from "@website/snippets/s_website_form/form";

const SIGNUP_FIELDS_SELECTOR = "#oe_structure_signup_fields";

/**
 * Gives the fields added in the signup form the behaviors they have in the form
 * snippets. Unlike a form snippet, the signup form is submitted by the browser
 * to `/web/signup`: it is only checked before being submitted, not sent to
 * form.js file.
 */
export class SignupForm extends Form {
    static selector = `form.oe_signup_form:has(${SIGNUP_FIELDS_SELECTOR})`;
    dynamicContent = {
        ...this.dynamicContent,
        ".s_website_form_send, .o_website_form_send": {},
        _root: { "t-on-submit.capture": this.onSubmit },
        ".s_website_form_multiple input[type='checkbox']": {
            "t-on-change": () => {},
            "t-att-required": (checkboxEl) => this.isCheckboxRequired(checkboxEl),
        },
    };

    setup() {
        super.setup();
        this.requiredCheckboxGroupEls = new Set(
            this.el.querySelectorAll(
                ".s_website_form_multiple:has(input[type='checkbox'][required])"
            )
        );
    }

    prefillValues() {
        const nameAttrByNonFieldEl = new Map(
            [...this.el.querySelectorAll("[name]")]
                .filter((el) => !("name" in el))
                .map((el) => [el, el.removeAttributeNode(el.attributes.name)])
        );
        super.prefillValues();
        for (const [nonFieldEl, nameAttr] of nameAttrByNonFieldEl) {
            nonFieldEl.setAttributeNode(nameAttr);
        }
    }

    /**
     * @param {HTMLInputElement} checkboxEl
     * @returns {boolean}
     */
    isCheckboxRequired(checkboxEl) {
        const groupEl = checkboxEl.closest(".s_website_form_multiple");
        return (
            this.requiredCheckboxGroupEls.has(groupEl) &&
            !groupEl.querySelector("input[type='checkbox']:checked")
        );
    }

    /**
     * Checks the form before it is submitted, and prevents submission if there
     * are errors. The standard fields of the signup form are required, and the
     * added fields are checked as in the form snippets.
     *
     * @param {SubmitEvent} ev
     */
    onSubmit(ev) {
        this.removeErrorMessages();
        if (!this.checkErrorFields({})) {
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
