import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";
import { registry } from "@web/core/registry";
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add("website_sale.custom_attribute_value", {
    steps: () => [
        {
            trigger: "li.js_attribute_value",
        },
        {
            trigger: 'li.js_attribute_value span:contains(Custom)',
            run: 'click',
        },
        {
            trigger: 'input.variant_custom_value',
            run: "edit Wood",
        },
        ...tourUtils.addToCartFromProductPage(),
        {
            trigger: 'button:contains(Go to Checkout)',
            run: 'click',
            expectUnloadPage: true,
        },
        ...tourUtils.assertCartContains({
            productName: 'Customizable Desk (TEST)',
            quantity: '1',
            description: 'Custom: Wood',
        }),
    ]
});
let optionVariantImage;

registry.category("web_tour.tours").add("website_sale.custom_attribute_value_advanced", {
    steps: () => [
        tourUtils.increaseProductPageQuantity(),
        tourUtils.assertProductPageStrikeThroughPrice('750.00'),
        ...tourUtils.addToCartFromProductPage(),
        {
            trigger: configuratorTourUtils.optionalProductSelector("Conference Chair (TEST) (Steel)"),
            run({ queryOne }) {
                optionVariantImage =
                    configuratorTourUtils.optionalProductImageSrc(queryOne, "Conference Chair (TEST) (Steel)")
            }
        },
        configuratorTourUtils.selectAttribute("Conference Chair", "Legs", "Aluminium"),
        {
            trigger: configuratorTourUtils.optionalProductSelector("Conference Chair (TEST) (Aluminium)"),
            run({ queryOne }) {
                const newOptionVariantImage =
                    configuratorTourUtils.optionalProductImageSrc(queryOne, "Conference Chair (TEST) (Aluminium)")
                if (newOptionVariantImage === optionVariantImage) {
                    console.error("The variant image wasn't updated");
                }
            }
        },
        configuratorTourUtils.assertOptionalProductPrice("Conference Chair", "22.90"),
        configuratorTourUtils.selectAttribute("Conference Chair", "Legs", "Steel"),
        configuratorTourUtils.addOptionalProduct("Conference Chair"),
        configuratorTourUtils.addOptionalProduct("Chair floor protection"),
        configuratorTourUtils.assertPriceTotal("1,228.50"),
        {
            trigger: 'button:contains(Go to Checkout)',
            run: 'click',
            expectUnloadPage: true,
        },
        ...tourUtils.assertCartContains({
            productName: "Customizable Desk (TEST)",
            backend: false,
        }),
    ]
});
