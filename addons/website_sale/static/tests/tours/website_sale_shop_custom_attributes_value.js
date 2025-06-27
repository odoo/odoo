/** @odoo-module **/

import { registry } from "@web/core/registry";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";
import * as tourUtils from '@website_sale/js/tours/tour_utils';

let optionVariantImage;

registry.category("web_tour.tours").add("a_shop_custom_attribute_value", {
    url: "/shop?search=Customizable Desk",
    steps: () => [{
        content: "click on Customizable Desk",
        trigger: '.oe_product_cart a:contains("Customizable Desk (TEST)")',
        run: "click",
        expectUnloadPage: true,
}, {
    trigger: 'a.js_add_cart_json:has(i.fa-plus)',
    run: 'click',
}, {
    trigger: 'span.oe_currency_value:contains(750)',
}, {
    id: 'add_cart_step',
    trigger: 'a:contains(Add to cart)',
    run: 'click',
}, {
    trigger: configuratorTourUtils.optionalProductSelector("Conference Chair (TEST) (Steel)"),
    run: function () {
        optionVariantImage =
            configuratorTourUtils.optionalProductImageSrc("Conference Chair (TEST) (Steel)")
    }
},
configuratorTourUtils.selectAttribute("Conference Chair", "Legs", "Aluminium"),
{
    trigger: configuratorTourUtils.optionalProductSelector("Conference Chair (TEST) (Aluminium)"),
    run: function () {
        const newOptionVariantImage =
            configuratorTourUtils.optionalProductImageSrc("Conference Chair (TEST) (Aluminium)")
        if (newOptionVariantImage === optionVariantImage) {
            console.error("The variant image wasn't updated");
        }
    }
},
configuratorTourUtils.assertOptionalProductPrice("Conference Chair", "22.90"),
configuratorTourUtils.selectAttribute("Conference Chair", "Legs", "Steel"),
configuratorTourUtils.addOptionalProduct("Conference Chair"),
configuratorTourUtils.addOptionalProduct("Chair floor protection"),
configuratorTourUtils.assertPriceTotal("1,528.50"),
{
    trigger: 'button:contains(Proceed to Checkout)',
    run: 'click',
    expectUnloadPage: true,
},
tourUtils.assertCartContains({
    productName: "Customizable Desk (TEST)",
    backend: false,
}),
]});
