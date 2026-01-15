import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_mrp_bom_product_catalog', {
    steps: () => [
        {
            trigger: 'button[name=action_add_from_catalog]',
            run: "click",
        },
        {
            trigger: '.o_kanban_record:nth-child(1)',
            run: "click",
        },
        {
            trigger: '.o_product_added',
            run: "click",
        },
        {
            trigger: 'button:contains("Back to BoM")',
            run: "click",
        },
        {
            trigger: 'div.o_field_one2many:contains("Component")',
        },
]});

registry.category("web_tour.tours").add('test_mrp_production_product_catalog', {
    steps: () => [
        {
            trigger: 'button[name=action_add_from_catalog_raw]',
            run: "click",
        },
        {
            trigger: '.o_kanban_record:nth-child(1)',
            run: "click",
        },
        {
            trigger: '.o_product_added',
            run: "click",
        },
        {
            trigger: 'button:contains("Back to Production")',
            run: "click",
        },
        {
            trigger: 'div.o_field_widget:contains("WH/MO/")',
        },
]});

registry.category("web_tour.tours").add('test_mrp_multi_step_product_catalog_component_transfer', {
    steps: () => [
        {
            trigger: 'button[name=action_add_from_catalog_raw]',
            run: "click",
        },
        {
            trigger: '.o_searchview_input',
            run: 'edit Wooden Leg',
        },
        {
            trigger: '.o_searchview_input',
            run: 'press Enter',
        },
        {
            content: "Wait for filtering",
            trigger: '.o_kanban_renderer:not(:has(.o_kanban_record:contains("Table")))',
        },
        {
            trigger: '.o_kanban_record:contains(Wooden Leg)',
            run: "click",
        },
        {
            trigger: '.o_kanban_record:contains(Wooden Leg) .o_product_catalog_quantity .o_input',
            run: 'edit 2',
        },
        {
            trigger: '.o_kanban_record:contains(Wooden Leg) .o_product_catalog_quantity .o_input',
            run: () => {
                const productQuantity = document.querySelector('.o_kanban_record .o_product_catalog_quantity .o_input').value;
                if (productQuantity !== "2") {
                    throw new Error(`Product quantity not correctly set to 2.`);
                }
            },
        },
        {
            content: "Force POL quantity update",
            trigger: 'button.o_facet_remove',
            run: "click",
        },
        {
            trigger: 'button:contains("Back to Production")',
            run: "click",
        },
        {
            trigger: 'div.o_field_widget:contains("WH/MO/")',
        },
        {
            trigger: '.o_data_row .o_field_mrp_should_consume:contains(2)',
        }
]});
