import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { Form } from "./form";
import { patch } from "@web/core/utils/patch";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export class FormEdit extends Interaction {
    static selector = ".s_website_form form, form.s_website_form"; // !compatibility
    start() {
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

    // Todo: remove in master
    _getDataForFields() {
        if (!this.dataForValues) {
            return [];
        }
        return Object.keys(this.dataForValues)
            .map((name) => this.el.querySelector(`[name="${CSS.escape(name)}"]`))
            .filter(
                (dataForValuesFieldEl) =>
                    dataForValuesFieldEl && dataForValuesFieldEl.name !== "email_to"
            );
    }
}

registry.category("public.interactions.edit").add("website.form", {
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
