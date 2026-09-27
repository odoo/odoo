import { FormController } from "@web/views/form/form_controller";
import { SaleTemplateDropdown } from "../components/template_dropdown";
import { patch } from "@web/core/utils/patch";

patch(FormController, {
    components: {
        ...FormController.components,
        SaleTemplateDropdown,
    },
});
