import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_barcode_duplication_error", {steps: () => [
    {
        trigger: "div.o_form_sheet div.o_notebook li button:contains('Sales')",
        run: "click",
    },
    {
        trigger: "div[name='uom_ids'] span.o_tag:contains('Pack of 6')",
        run: "click",
    },
    {
        trigger: "div.modal-content",
    },
    {
        trigger: "div[name='product_uom_ids'] input",
        run: "edit test-1234",
    },
    {
        trigger: "div[name='product_uom_ids'] ul li.o_m2o_dropdown_option_create",
        run: "click",
    },
    {
        trigger: "div.modal-content.o_error_dialog main:contains('The operation cannot be completed: A barcode can only be assigned to one packaging.')",
    }
]});
