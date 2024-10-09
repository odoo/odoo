/** @odoo-module **/

import { registry } from "@web/core/registry";
import { clickOnEditAndWaitEditModeInTranslatedPage } from "@website/js/tours/tour_utils";

registry.category("web_tour.tours").add('edit_translated_page_redirect', {
    url: '/nl/contactus',
    steps: () => [
    {
        content: "Enter backend",
        trigger: 'a.o_frontend_to_backend_edit_btn',
        run: "click",
    },
    {
        content: "Check the data-for attribute",
        trigger: ':iframe main:has([data-for="contactus_form"])',
    },
    ...clickOnEditAndWaitEditModeInTranslatedPage(),
    {
        content: "Go to /nl",
        trigger: "body",
        run: () => {
            // After checking the presence of the editor dashboard, we visit a
            // translated version of the homepage. The homepage is a special
            // case (there is no trailing slash), so we test it separately.
            location.href = '/nl';
        },
    },
    {
        content: "Enter backend",
        trigger: 'a.o_frontend_to_backend_edit_btn',
        run: "click",
    },
    ...clickOnEditAndWaitEditModeInTranslatedPage(),
]});
