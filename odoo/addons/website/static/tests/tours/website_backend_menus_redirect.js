/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('website_backend_menus_redirect', {
    test: true,
    url: '/',
    steps: () => [
{
    content: 'Need at least a step so the tour is not failing in enterprise',
    trigger: 'body',
    edition: 'enterprise',
}, {
    content: 'Make frontend to backend menus appears',
    trigger: 'body:has(#wrap)',
    run: function () {
        // The dropdown is hidden behind an SVG on hover animation.
        this.$anchor.find('.o_frontend_to_backend_apps_menu').addClass('show');
    },
    edition: 'community',
}, {
    content: 'Click on Test Root backend menu',
    trigger: '.o_frontend_to_backend_apps_menu a:contains("Test Root")',
    edition: 'community',
}, {
    content: 'Check that we landed on the apps page (Apps), and not the Home Action page (Settings)',
    trigger: '.oe_module_vignette',
    edition: 'community',
}
]});
