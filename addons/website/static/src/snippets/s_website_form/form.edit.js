import { registry } from "@web/core/registry";
import {
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";
const { DateTime } = luxon;
import { Form } from "./form";

const FormEdit = I => class extends I {
    setup() {
        super.setup();
        this.editTranslations = this.services.website_edit.isEditingTranslations();
    }

    prepareDateFields() {
        // We do not initialize the datetime picker in edit mode but want the dates to be formated
        this.el.querySelectorAll(".s_website_form_input.datetimepicker-input").forEach(el => {
            const value = el.getAttribute("value");
            if (value) {
                const format =
                    el.closest(".s_website_form_field").dataset.type === "date"
                        ? formatDate
                        : formatDateTime;
                    el.value = format(DateTime.fromSeconds(parseInt(value)));
            }
        });
        // Do not call super !
    }

    prefillValues() {
        if (this.editTranslations) {
            return;
        }
        super.prefillValues();
    }
};

registry
    .category("website.editable_active_elements_builders")
    .add("website.form", {
        Interaction: Form,
        mixin: FormEdit,
    });
