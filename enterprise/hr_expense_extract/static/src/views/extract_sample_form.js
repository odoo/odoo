import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { ExtractSampleFormController } from "@hr_expense_extract/views/extract_sample_controller";

export const ExtractSampleFormView = {
    ...formView,
    Controller: ExtractSampleFormController,
};

registry.category("views").add("extract_sample_form", ExtractSampleFormView);
