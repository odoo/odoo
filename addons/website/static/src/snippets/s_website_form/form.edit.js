import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { Form } from "./form";

import { patch } from "@web/core/utils/patch";
import {
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";
const { DateTime } = luxon;

export class FormDateFormatterEdit extends Interaction {
    static selector = ".s_website_form form .s_website_form_field .s_website_form_input.datetimepicker-input, form.s_website_form .s_website_form_field .s_website_form_input.datetimepicker-input"; // !compatibility

    start() {
        // We do not initialize the datetime picker in edit mode but want the dates to be formatted.
        const value = this.el.getAttribute("value");
        if (value) {
            const format =
                this.el.closest(".s_website_form_field").dataset.type === "date"
                    ? formatDate
                    : formatDateTime;
            this.el.value = format(DateTime.fromSeconds(parseInt(value)));
        }
    }
}

registry
    .category("public.interactions.edit")
    .add("website.form_date_formatter", {
        Interaction: FormDateFormatterEdit,
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
