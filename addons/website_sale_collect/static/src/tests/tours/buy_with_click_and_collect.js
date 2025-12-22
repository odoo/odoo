import {registry} from '@web/core/registry';
import {clickOnElement} from '@website/js/tours/tour_utils';
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category('web_tour.tours').add('website_sale_collect_widget', {
    url: '/shop',
    steps: () => [
        ...tourUtils.searchProduct("Test CAC Product", { select: true }),
        clickOnElement("Open Location selector", '.o_click_and_collect_availability'),
        {
            content: "Check the dialog is opened",
            trigger: '.o_location_selector',
        },
        clickOnElement("Choose location", '#submit_location_large'),
        {
            content: "Check pickup location is set",
            trigger: '.o_click_and_collect_availability strong:contains("Shop 1")',
        },
    ],
});
