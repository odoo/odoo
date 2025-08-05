import { addSectionFromProductCatalog } from "@account/js/tours/tour_utils";
import { selectPOVendor } from "./tour_helper";
import { registry } from "@web/core/registry";

const openSearchPanelStep = {
    content: "Open Search Panel if it is closed",
    trigger: '.o_search_panel_sidebar',
    run: 'click',
};

registry.category("web_tour.tours").add('test_add_section_from_product_catalog_on_purchase_order', {
    steps: () => {
        const steps = [
            {
                content: "Create a new PO",
                trigger: '.o_list_button_add',
                run: 'click',
            },
            ...selectPOVendor("Test Vendor"),
        ];

        const catalogSteps = addSectionFromProductCatalog();
        catalogSteps.splice(1, 0, openSearchPanelStep);
        catalogSteps.splice(5, 0, openSearchPanelStep);

        return [...steps, ...catalogSteps];
    },
});
