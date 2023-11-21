/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('website_backend_menus_redirect', {
    test: true,
    url: '/',
},
[{
    content: 'Need at least a step so the tour is not failing in enterprise',
    trigger: 'body',
    edition: 'enterprise',
}, {
    content: 'Make frontend to backend menus appears',
    trigger: '#oe_applications a',
    edition: 'community',
}, {
    content: 'Click on Test Root backend menu',
    trigger: '#oe_applications a:contains("Test Root")',
    edition: 'community',
}, {
    content: 'Check that we landed on the apps page (Apps), and not the Home Action page (Settings)',
    trigger: '.oe_module_vignette',
    edition: 'community',
},
]);
