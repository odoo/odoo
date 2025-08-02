import { addSectionFromProductCatalog } from "@account/js/tours/tour_utils";
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
            {
                content: "Select the customer field",
                trigger: '.o_field_res_partner_many2one input.o_input',
                run: 'click',
            },
            {
                content: "Wait for the field to be active",
                trigger: '.o_field_res_partner_many2one input[aria-expanded=true]',
            },
            {
                trigger: ".o_field_res_partner_many2one[name='partner_id'] input",
                content: "Search a vendor name",
                tooltipPosition: "bottom",
                async run(actions) {
                    const input = this.anchor.querySelector("input");
                    await actions.edit("Test Vendor", input || this.anchor);
                },
            },
            {
                isActive: ["auto"],
                trigger: '.ui-menu-item > a:contains("Test Vendor")',
                run: 'click',
            },
        ];

        const catalogSteps = addSectionFromProductCatalog();
        catalogSteps.splice(1, 0, openSearchPanelStep);
        catalogSteps.splice(5, 0, openSearchPanelStep);

        return [...steps, ...catalogSteps];
    },
});
