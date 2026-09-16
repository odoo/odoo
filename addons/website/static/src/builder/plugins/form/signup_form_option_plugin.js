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
// the `website.website_signup_extra_fields` template). Their values are handled
// by `WebsiteAuthSignupHome`.
const SIGNUP_FIELDS_SELECTOR = "#oe_structure_signup_fields";

/**
 * Adds a custom field in the area of the signup form dedicated to them: at its
 * end when the form is given, after the given field otherwise. The field copies
 * the layout of the one before it or, for the first one, the layout of the
 * standard signup fields.
 *
 * @param {HTMLElement} el the signup form, or one of the fields added in it
 * @param {Function} renderToElement
 * @returns {HTMLElement} the added field
 */
function addSignupField(el, renderToElement) {
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
    const fieldEl = renderField(field, renderToElement);
    if (isFormEl) {
        sectionEl.append(fieldEl);
    } else {
        el.after(fieldEl);
    }
    return fieldEl;
}

export class SignupFormOptionPlugin extends Plugin {
    static id = "websiteSignupFormOption";
    static dependencies = ["builderOptions", "websiteBridge", "websiteFormOption"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_header_middle_buttons: {
            Component: FormOptionAddFieldButton,
            selector: `form.oe_signup_form:has(${SIGNUP_FIELDS_SELECTOR})`,
            editableOnly: false,
            props: {
                addField: (formEl) =>
                    this.dependencies.builderOptions.setNextTarget(
                        addSignupField(formEl, this.dependencies.websiteBridge.renderToElement)
                    ),
                tooltip: _t("Add a new field at the end"),
            },
        },
        on_will_save_handlers: this.whitelistFields.bind(this),
    };

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

patch(FormOptionPlugin.prototype, {
    addField(editingElement) {
        if (!editingElement.matches(`${SIGNUP_FIELDS_SELECTOR} > *`)) {
            return super.addField(...arguments);
        }
        // A field added after a signup field keeps its layout: the signup
        // fields have no "Labels Position" option to change it afterwards.
        this.dependencies.builderOptions.setNextTarget(
            addSignupField(editingElement, this.dependencies.websiteBridge.renderToElement)
        );
    },
});

registry.category("website-plugins").add(SignupFormOptionPlugin.id, SignupFormOptionPlugin);
