import { addSectionFromProductCatalog } from "@account/js/tours/tour_utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_use_product_catalog_on_invoice", {
    steps: () => [
        {
            content: "Click Catalog Button",
            trigger: "button[name=action_add_from_catalog]",
            run: "click",
        },
        {
            content: "Add a Product",
            trigger: ".o_kanban_record:contains(Test Product)",
            run: "click",
        },
        {
            content: "Wait for it",
            trigger: ".o_product_added",
        },
        {
            content: "Back to Invoice",
            trigger: ".o-kanban-button-back",
            run: "click",
        },
        {
            content: "Ensure product is added",
            trigger: ".o_field_product_label_section_and_note_cell:contains(Test Product)",
        },
    ],
});

registry.category("web_tour.tours").add('test_add_section_from_product_catalog_on_invoice', {
    steps: () => addSectionFromProductCatalog()
});
