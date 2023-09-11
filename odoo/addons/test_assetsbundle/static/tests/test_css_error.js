/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('css_error_tour', {
    test: true,
    url: '/web',
    steps: () => [
    {
        content: "Error message",
        trigger: ".modal-body",
        run: () => {},
    },
]});


registry.category("web_tour.tours").add('css_error_tour_frontend', {
    test: true,
    url: '/',
    steps: () => [
    {
        content: "Error message",
        trigger: ".modal-body",
        run: () => {},
    },
]});

// Note, the ideal steap would be `.modal-body:contains('Error: Invalid CSS after \".rule1\": expected selector, was \"()){ /* error */')` but it fails sometimes
