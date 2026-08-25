import { patch } from "@web/core/utils/patch";
import { NewQuotationButton } from "@sale/views/widgets/new_quotation_button/new_quotation_button";
import { SaleTemplateDropdown } from "../../components/template_dropdown";

patch(NewQuotationButton, {
    components: {
        ...NewQuotationButton.components,
        SaleTemplateDropdown,
    },
});
