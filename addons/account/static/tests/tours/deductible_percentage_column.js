import { registry } from '@web/core/registry';
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("deductible_percentage_column", {
    steps: () => [
    {
        content: "Add item",
        trigger: "div[name='invoice_line_ids'] .o_field_x2many_list_row_add button:contains('Add a line')",
        run: "click",
    },
    {
        content: "Edit name",
        trigger: ".o_field_widget[name='name'] .o_input",
        run: "edit Laptop"
    },
    {
        content: "Edit deductible percentage",
        trigger: ".o_field_widget[name='deductible_percentage'] .o_input",
        run: "edit 80"
    },
    {
        content: "Set Bill Date",
        trigger: "input[data-field=invoice_date]",
        run: "edit 2025-12-01",
    },
    ...stepUtils.saveForm(),
]})
