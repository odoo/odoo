import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { Form } from "./form";
import { patch } from "@web/core/utils/patch";
import {
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";
import wUtils from "@website/js/utils";

const { DateTime } = luxon;

export class FormEdit extends Interaction {
    static selector = ".s_website_form form, form.s_website_form"; // !compatibility
    start() {
        // The "data-for" values were removed (on destroy before saving),
        // but we still need to restore them in edit mode in the case of
        // a simple widget refresh.
        this.dataForValues = wUtils.getParsedDataFor(this.el.id, this.el.ownerDocument);
        for (const fieldEl of this._getDataForFields()) {
            if (!fieldEl.getAttribute("value")) {
                fieldEl.setAttribute("value", this.dataForValues[fieldEl.name]);
            }
        }

        // We do not initialize the datetime picker in edit mode but want the dates to be formatted.
        for (const el of this.el.querySelectorAll(".s_website_form_input.datetimepicker-input")) {
            const value = el.getAttribute("value");
            if (value) {
                const format =
                    el.closest(".s_website_form_field").dataset.type === "date"
                        ? formatDate
                        : formatDateTime;
                el.value = format(DateTime.fromSeconds(parseInt(value)));
            }
        }
    }

    destroy() {
        // The "data-for" values are always correctly added to the form on the
        // form interaction start. But if we make any change to it in "edit"
        // mode, we need to be sure it will not be saved with the new values.
        for (const fieldEl of this._getDataForFields()) {
            fieldEl.removeAttribute("value");
        }
    }

    _getDataForFields() {
        if (!this.dataForValues) {
            return [];
        }
        return Object.keys(this.dataForValues)
            .map(name => this.el.querySelector(`[name="${CSS.escape(name)}"]`))
            .filter(dataForValuesFieldEl => dataForValuesFieldEl && dataForValuesFieldEl.name !== "email_to");
    }
}

registry
    .category("public.interactions.edit")
    .add("website.form", {
        Interaction: FormEdit,
    });

// Translation mode.
patch(Form.prototype, {
    setup() {
        super.setup();
        this.editTranslations = this.services.website_edit.isEditingTranslations();
    },
    prefillValues() {
        if (this.editTranslations) {
            return;
        }
        super.prefillValues();
    },
});
