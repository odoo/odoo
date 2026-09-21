import {
    addSectionFromProductCatalog,
    showProductColumn,
} from "@account/js/tours/tour_utils";
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
        ...showProductColumn(),
        {
            content: "Ensure product is added",
            trigger:
                ".o_field_product_label_section_and_note_cell:contains(Test Product)",
        },
    ],
});

registry
    .category("web_tour.tours")
    .add("test_add_section_from_product_catalog_on_invoice", {
        steps: () => addSectionFromProductCatalog(),
    });

registry
    .category("web_tour.tours")
    .add("test_product_lands_in_the_section_created_from_the_catalog", {
        steps: () => {
            const [openCatalog, ...createSectionAndAddProduct] =
                addSectionFromProductCatalog().slice(0, -2);
            return [
                openCatalog,
                // A product card is set up once, and on a fresh catalog that
                // happens while the sections are still loading. Emptying the
                // kanban and filling it again sets the cards up after the panel
                // selected "No Section" -- the order a slow machine gives, and
                // the one in which a card that remembered the selection of its
                // setup put the product outside the section created afterwards.
                {
                    content: "Search for a product that does not exist",
                    trigger: ".o_searchview_input",
                    run: "edit no such product",
                },
                {
                    content: "Validate the search",
                    trigger: ".o_searchview_autocomplete .o-dropdown-item:first",
                    run: "click",
                },
                {
                    content: "No card is left",
                    trigger:
                        ".o_kanban_renderer:not(:has(.o_kanban_record:not(.o_kanban_ghost)))",
                },
                {
                    content: "Clear the search, so the cards are set up now",
                    trigger: ".o_searchview_facet .o_facet_remove",
                    run: "click",
                },
                {
                    content: "The product is back",
                    trigger: '.o_kanban_record:contains("Test Product")',
                },
                ...createSectionAndAddProduct,
                {
                    content: "The line the invoice already had stays first",
                    trigger:
                        ".o_section_and_note_list_view tbody tr:nth-child(1):not(.o_is_line_section)",
                },
                {
                    content: "The new section follows it",
                    trigger:
                        ".o_section_and_note_list_view tbody tr:nth-child(2).o_is_line_section",
                },
                {
                    content: "The product added from the catalog is inside the section",
                    trigger:
                        '.o_section_and_note_list_view tbody tr:nth-child(3):contains("Test Product")',
                },
            ];
        },
    });
