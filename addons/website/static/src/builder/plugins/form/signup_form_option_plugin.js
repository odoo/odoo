import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { FormOption } from "./form_option";
import { FormOptionAddFieldButton } from "./form_option_add_field_button";
import { FormOptionPlugin } from "./form_option_plugin";
import { getCustomField, getFieldFormat, renderField } from "./utils";

// The signup form is not a form snippet: it is the standard `auth_signup.signup`
// form, in which an `oe_structure` holds the fields added from the editor (see
// the `website.signup_extra_fields` template). Their values are handled by
// `WebsiteAuthSignupHome`.
const SIGNUP_FIELDS_SELECTOR = "#oe_structure_signup_fields";

/**
 * Adds a custom field to the signup form: at the end of its fields area when
 * given the form, after the given field otherwise. The new field copies the
 * layout of the field before it or, for the first one, the layout of the
 * standard signup fields: signup fields have no "Labels Position" option.
 *
 * @param {HTMLElement} el the signup form, or one of the fields added in it
 * @returns {HTMLElement} the new field
 */
function addSignupField(el) {
    const isFormEl = el.matches("form");
    const sectionEl = isFormEl ? el.querySelector(SIGNUP_FIELDS_SELECTOR) : el.parentElement;
    const previousFieldEl = isFormEl
        ? [...sectionEl.querySelectorAll(".s_website_form_field")].at(-1)
        : el;
    const field = getCustomField("char", _t("Custom Text"));
    field.formatInfo = previousFieldEl
        ? getFieldFormat(previousFieldEl)
        : {
              labelPosition: "top",
              multiPosition: "horizontal",
              textPosition: "stacked",
              labelInvisible: false,
          };
    const fieldEl = renderField(field);
    if (isFormEl) {
        sectionEl.append(fieldEl);
    } else {
        el.after(fieldEl);
    }
    return fieldEl;
}

export class SignupFormOptionPlugin extends Plugin {
    static id = "websiteSignupFormOption";
    static dependencies = ["builderOptions", "websiteFormOption"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_header_middle_buttons: {
            Component: FormOptionAddFieldButton,
            selector: "form.oe_signup_form:has(#oe_structure_signup_fields)",
            editableOnly: false,
            props: {
                addField: this.addField.bind(this),
                tooltip: _t("Add a new field at the end"),
            },
        },
        on_will_save_handlers: this.whitelistFields.bind(this),
    };

    /**
     * @param {HTMLElement} formEl
     */
    addField(formEl) {
        this.dependencies.builderOptions.setNextTarget(addSignupField(formEl));
    }

    /**
     * Opts the existing fields added on the signup form in the form builder, as
     * for the form snippets. `FormOption.cleanForSave` looks for the forms of
     * form snippets: it is given a copy of the signup form within one.
     *
     * @param {HTMLElement} el
     */
    async whitelistFields(el) {
        const formEl = el.querySelector(SIGNUP_FIELDS_SELECTOR)?.closest("form");
        if (!formEl) {
            return;
        }
        const snippetEl = document.createElement("div");
        snippetEl.classList.add("s_website_form");
        snippetEl.append(formEl.cloneNode(true));
        await FormOption.cleanForSave(snippetEl, {
            dependencies: this.dependencies,
            services: this.services,
        });
    }
}

// The "+ Field" button of each field (see `FormOptionPlugin`) adds the new field
// with the layout of the form snippets (labels on the left).
patch(FormOptionPlugin.prototype, {
    addField(editingElement) {
        if (!editingElement.matches(`${SIGNUP_FIELDS_SELECTOR} > *`)) {
            return super.addField(...arguments);
        }
        this.dependencies.builderOptions.setNextTarget(addSignupField(editingElement));
    },
    // The marks settings of the signup fields are saved on their area: the
    // signup form itself is not saved.
    setLabelsMark(formEl) {
        return super.setLabelsMark(formEl.querySelector(SIGNUP_FIELDS_SELECTOR) || formEl);
    },
});

registry.category("website-plugins").add(SignupFormOptionPlugin.id, SignupFormOptionPlugin);
