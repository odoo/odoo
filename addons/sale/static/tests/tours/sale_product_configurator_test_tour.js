/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('sale_product_configurator_test_tour', {
    steps: () => [
        {
            trigger: "td[name='product_template_id']",
            content: "Click on the product line to activate it.",
            run: 'click',
        },
        {
            trigger: "tr.o_data_row td[name='product_template_id'] input.o-autocomplete--input.o_input.pe-3[placeholder='Search a product']",
            content: "Clear the product from the line.",
            run: 'edit',
        },
        {
            trigger: "input.o_input[type='text'][inputmode='decimal'][autocomplete='off']",
            content: "Click on the decimal input field.",
            run: 'click',
        },
        {
            trigger: "button.btn.btn-secondary.fa.fa-pencil.px-2[aria-label='Edit Configuration'][data-tooltip='Edit Configuration']",
            content: "Click to edit the product configuration.",
            run: 'click',
        },
        {
            trigger: "i.fa.fa-times.fa-fw",
            content: "Click to close or remove.",
            run: 'click',
        },
    ]
});
