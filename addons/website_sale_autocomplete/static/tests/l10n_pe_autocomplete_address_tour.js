import { registry } from "@web/core/registry";
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('autocomplete_pe_tour', {
    url: '/shop', 
    steps: () => [
        ...tourUtils.addToCart({ productName: "A test product", expectUnloadPage: true }),
        tourUtils.goToCart(),
        tourUtils.goToCheckout(),
        
        {
            content: 'Type address in street field',
            trigger: 'input[name="street"]',
            run: "edit Avenida Larco",
        }, {
            content: 'Wait for results to appear',
            trigger: '.js_autocomplete_result',
        }, {
            content: 'Click the first mock result',
            trigger: ".dropdown-menu .js_autocomplete_result:first:contains(Peru Result 0)",
            run: "click",
        },
        {
            content: 'Check that City ID (Province) is selected (not the placeholder)',
            trigger: 'select[name="city_id"]:value(/^[0-9]+$/)',
        }, {
            content: 'Check Zip code value',
            trigger: 'input[name="zip"]:value(/^15001$/)',
        }
    ]
});
