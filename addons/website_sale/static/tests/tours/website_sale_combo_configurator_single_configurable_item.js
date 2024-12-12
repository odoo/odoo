import { registry } from '@web/core/registry';

registry
    .category('web_tour.tours')
    .add('website_sale_combo_configurator_single_configurable_item', {
        url: '/shop?search=Combo product',
        steps: () => [
            {
                content: "Select Combo product",
                trigger: '.oe_product_cart a:contains("Combo product")',
                run: 'click',
            },
            {
                content: "Click on add to cart",
                trigger: '#add_to_cart',
                run: 'click',
            },
            {
                content: "Assert that the combo configurator is shown",
                trigger: '.sale-combo-configurator-dialog',
            },
        ],
   });
