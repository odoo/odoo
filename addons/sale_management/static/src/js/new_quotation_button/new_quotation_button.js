import { patch } from "@web/core/utils/patch";
import { NewQuotationButton } from "@sale/js/new_quotation_button/new_quotation_button";
import { SaleTemplateDropdown } from "../../views/components/template_dropdown";

patch(NewQuotationButton, {
    template: "sale_management.SaleManagementQuotationButton",
    components: {
        ...NewQuotationButton.components,
        SaleTemplateDropdown,
    },
});
