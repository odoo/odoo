import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('autocomplete_br_tour', {
    url: '/shop',
    steps: () => [
        ...tourUtils.addToCart({ productName: "A test product", expectUnloadPage: true }),
        tourUtils.goToCart(),
        tourUtils.goToCheckout(),
        {
            content: "Set Brazil first",
            trigger: 'select[name="country_id"]',
            run: "selectByLabel Brazil",
        },
        {
            content: 'Input in Street field (handles both standard and extended)',
            trigger: 'input[name="street_name"]',
            run: "edit Hello",
        },
        {
            content: 'Wait for results',
            trigger: '.js_autocomplete_result',
        },
        {
            content: 'Click result 0',
            trigger: ".dropdown-menu .js_autocomplete_result:first",
            run: "click",
        },
        {
            content: 'Check Street Name (Extended)',
            trigger: 'input[name="street_name"]:value(Hello world)',
        },
        {
            content: 'Check Zip code',
            trigger: 'input[name="zip"]:value(12345)',
        },
        {
            content: 'Check Street 2',
            trigger: 'input[name="street2"]:value(Bye Bye)',
        },
    ],
});
