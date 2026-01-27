import { registry } from '@web/core/registry';
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("deductible_amount_column", {
    url: "/odoo/vendor-bills/new",
    steps: () => [
    {
        content: "Add item",
        trigger: "div[name='invoice_line_ids'] .o_field_x2many_list_row_add a:contains('Add a line')",
        run: "click",
    },
    {
        content: "Edit name",
        trigger: ".o_field_widget[name='name'] .o_input",
        run: "edit Laptop"
    },
    {
        content: "Edit deductible amount",
        trigger: ".o_field_widget[name='deductible_amount'] > .o_input",
        run: "edit 80"
    },
    {
        content: "Set Bill Date",
        trigger: "input[data-field=invoice_date]",
        run: "edit 2025-12-01",
    },
    ...stepUtils.saveForm(),
]})
