import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("purchase_order_section_duplicate_tour", {
    steps: () => [
        {
            content: "Open section option dropdown (:)",
            trigger: ".o_data_row.o_is_line_section:eq(0) .o_list_section_options button.dropdown-toggle",
            run: "click",
        },
        {
            content: "Duplicate Section",
            trigger: ".o-dropdown-item:contains('Duplicate')",
            run: "click",
        },
        {
            content: "Save Order",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "Check the order saved without error",
            trigger: ".o_form_view .o_form_saved",
        },
    ],
});
