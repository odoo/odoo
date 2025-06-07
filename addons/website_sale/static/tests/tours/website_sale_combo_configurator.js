import { registry } from '@web/core/registry';
import { queryValue, waitUntil } from '@odoo/hoot-dom';
import comboConfiguratorTourUtils from '@sale/js/tours/combo_configurator_tour_utils';
import productConfiguratorTourUtils from '@sale/js/tours/product_configurator_tour_utils';
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('website_sale_combo_configurator', {
        url: '/shop?search=Combo product',
        steps: () => [
            ...wsTourUtils.addToCart({ productName: "Combo product", search: false }),
            // Assert that the combo configurator behaves as expected.
            comboConfiguratorTourUtils.assertFooterButtonsDisabled(),
            comboConfiguratorTourUtils.setQuantity(3),
            comboConfiguratorTourUtils.selectComboItem("Product A1"),
            ...productConfiguratorTourUtils.selectAndSetCustomAttribute(
                "Product A1", "No variant attribute", "B", "Some custom value"
            ),
            ...productConfiguratorTourUtils.saveConfigurator(),
            comboConfiguratorTourUtils.selectComboItem("Product B2"),
            comboConfiguratorTourUtils.assertFooterButtonsEnabled(),
            // Assert that the cart's content is correct.
            {
                content: "Proceed to checkout",
                trigger: 'button:contains(Proceed to Checkout)',
                run: 'click',
            },
            wsTourUtils.assertCartContains({ productName: "Combo product" }),
            wsTourUtils.assertCartContains({ productName: "3 x Product A1" }),
            wsTourUtils.assertCartContains({ productName: "3 x Product B2" }),
            {
                content: "Verify the first combo item's attributes",
                trigger: 'div.o_cart_product:contains("No variant attribute: B: Some custom value")',
            },
            {
                content: "Verify the combo product's quantity",
                trigger: 'input.quantity',
                run: async () => await waitUntil(
                    () => queryValue('input.quantity') === '3', { timeout: 1000 }
                ),
            },
            {
                content: "Verify the combo product's price",
                trigger: 'div[name="website_sale_cart_line_price"]:contains(93.00)',
            },
            {
                content: "Verify the order's total price",
                trigger: 'tr#order_total_untaxed:contains(93.00)',
            },
            // Assert that the combo quantity can be updated in the cart.
            {
                content: "Edit the combo quantity",
                trigger: 'input.quantity',
                run: 'edit 2 && click body',
            },
            wsTourUtils.assertCartContains({ productName: "2 x Product A1" }),
            wsTourUtils.assertCartContains({ productName: "2 x Product B2" }),
            {
                content: "Verify the combo product's price",
                trigger: 'div[name="website_sale_cart_line_price"]:contains(62.00)',
            },
        ],
   });
