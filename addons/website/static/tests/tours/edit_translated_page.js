/** @odoo-module **/

import tour from "web_tour.tour";

tour.register('edit_translated_page_redirect', {
    test: true,
    url: '/nl/contactus',
}, [
    {
        content: 'click edit master',
        trigger: 'a[data-action="edit_master"]',
    },
    {
        content: 'check editor dashboard',
        trigger: '#oe_snippets',
        run: () => {
            // After checking the presence of the editor dashboard, we visit a
            // translated version of the homepage. The homepage is a special
            // case (there is no trailing slash), so we test it separately.
            location.href = '/nl';
        },
    },
    {
        content: 'click edit master',
        trigger: 'a[data-action="edit_master"]',
    },
    {
        content: 'check editor dashboard',
        trigger: '#oe_snippets',
        run: () => {},
    },
]);
