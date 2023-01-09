/** @odoo-module **/

import tour from "web_tour.tour";

tour.register('edit_translated_page_redirect', {
    test: true,
    url: '/nl/contactus',
}, [
    {
        content: "Enter backend",
        trigger: 'a.o_frontend_to_backend_edit_btn',
    },
    {
        content: "Enter edit mode",
        extra_trigger: 'iframe main:has([data-for="contactus_form"])',
        trigger: '.o_edit_website_container > a',
    },
    {
        content: 'check editor dashboard',
        trigger: '#oe_snippets.o_loaded',
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
    {
        content: "Enter edit mode",
        extra_trigger: 'iframe #wrapwrap',
        trigger: '.o_edit_website_container > a',
    },
    {
        content: 'check editor dashboard',
        trigger: '#oe_snippets.o_loaded',
        run: () => {},
    },
]);
