import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { parseDate, parseDateTime, serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { Form } from "@website/snippets/s_website_form/form";

// Area of the signup form holding the fields added from the website editor (see
// the `website.signup_extra_fields` template).
const SIGNUP_FIELDS_SELECTOR = "#oe_structure_signup_fields";

/**
 * Gives the fields added in the signup form the behaviors they have in the form
 * snippets (visibility rules, date pickers, requirements, files, ...). Unlike a
 * form snippet, the signup form is submitted by the browser to `/web/signup`:
 * it is only checked before being submitted, not sent (see `Form.send`).
 */
export class SignupForm extends Form {
    static selector = `form.oe_signup_form:has(${SIGNUP_FIELDS_SELECTOR})`;
    dynamicContent = {
        ...this.dynamicContent,
        ".s_website_form_send, .o_website_form_send": {},
        // Capture: the form is checked before the other `submit` handlers run
        // (e.g. the reCAPTCHA one, which submits the form itself).
        _root: { "t-on-submit.capture": this.onSubmit },
        // All the checkboxes of a required field are rendered as required, so
        // that the browser validation requires every one of them to be checked.
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
     * The browser validated the form before this event: check what it cannot
     * (e.g. requirement rules, files) and prepare the submitted values.
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
        // As in `Form.send`, the dates of existing fields are posted in the
        // server format.
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

/**
 * The marks of the signup fields are set on their area, but the standard fields
 * of the form (name, email, password) are not form builder fields: their mark is
 * displayed in CSS, from the settings of the area set on the form.
 */
export class SignupFormMarks extends Interaction {
    static selector = `form.oe_signup_form:has(${SIGNUP_FIELDS_SELECTOR})`;
    dynamicContent = {
        _root: {
            "t-att-style": () => ({
                "--signup-form-mark": this.mark,
                "--signup-form-mark-color": this.markColor,
            }),
        },
    };

    setup() {
        this.sectionEl = this.el.querySelector(SIGNUP_FIELDS_SELECTOR);
        this.readMarkSettings();
        // The settings change while the page is edited.
        const observer = new MutationObserver(() => {
            this.readMarkSettings();
            this.updateContent();
        });
        observer.observe(this.sectionEl, {
            attributes: true,
            attributeFilter: ["class", "data-mark", "style"],
        });
        this.registerCleanup(() => observer.disconnect());
    }

    readMarkSettings() {
        const { classList, dataset, style } = this.sectionEl;
        // The standard fields are all required.
        this.mark =
            classList.contains("o_mark_required") && dataset.mark
                ? JSON.stringify(` ${dataset.mark}`)
                : undefined;
        this.markColor = style.getPropertyValue("--form-label-required-mark-color") || undefined;
    }
}

registry
    .category("public.interactions")
    .add("website.signup_form", SignupForm)
    .add("website.signup_form_marks", SignupFormMarks);

registry.category("public.interactions.edit").add("website.signup_form_marks", {
    Interaction: SignupFormMarks,
});
