/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

patch(registry.category("web_tour.tours").get("industry_fsm_sale_products_tour"), {
    steps() {
        const originalSteps = super.steps();
        const fsmStockIndex = originalSteps.findIndex((step) => step.id === "fsm_stock_start");
        originalSteps.splice(fsmStockIndex  + 1, 0, {
            trigger: '.o_fsm_product_kanban_view .o_kanban_group:has(.o_kanban_header:has(span:contains("Service"))) .o_kanban_record:has(span:contains("Acoustic Bloc Screens"))',
            content: 'Add 1 quantity to the Service product',
            run: "click",
        }, {
            trigger: '.o_fsm_product_kanban_view .o_kanban_group:has(.o_kanban_header:has(span:contains("Service"))) .o_kanban_record:has(span:contains("Acoustic Bloc Screens"))',
            content: 'Add 1 quantity to the Service product',
            run: "click",
        }, {
            trigger: '.o_fsm_product_kanban_view .o_kanban_group:has(.o_kanban_header:has(span:contains("Service"))) .o_kanban_record:has(span:contains("Acoustic Bloc Screens")) button:has(i.fa-minus:not([disabled]))',
            content: 'Check that the quantity of the Service product is still decreasable even though it is considered delivered by default',
            run: "click",
        }, {
            trigger: '.o_fsm_product_kanban_view .o_kanban_group:has(.o_kanban_header:has(span:contains("Service"))) .o_kanban_record:has(span:contains("Acoustic Bloc Screens")) .o_product_catalog_buttons .fa-trash',
            content: 'Check that the quantity of the Service product is still removable even though it is considered delivered by default',
            run: "click",
        }, {
            trigger: '.o_fsm_product_kanban_view .o_kanban_group:has(.o_kanban_header:has(span:contains("Service"))) .o_kanban_record:has(span:contains("Acoustic Bloc Screens")) .o_product_catalog_buttons .fa-shopping-cart',
            content: 'Check that the quantity of the Service product were correctly removed',
        });
        return originalSteps;
    }
});
