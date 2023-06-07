/** @odoo-module **/

import tour from "web_tour.tour";
import wTourUtils from "website.tour_utils";

tour.register('edit_translated_page_redirect', {
    test: true,
    url: '/nl/contactus',
}, [
    {
        content: "Enter backend",
        trigger: 'a.o_frontend_to_backend_edit_btn',
    },
    {
        content: "Check the data-for attribute",
        trigger: 'iframe main:has([data-for="contactus_form"])',
        run: () => {}, // it's a check
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
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
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
]);
