odoo.define('website.tour.specific_website_editor', function (require) {
'use strict';

const { registry } = require("@web/core/registry");

registry.category("web_tour.tours").add('generic_website_editor', {
    test: true,
    steps: [{
    content: 'Click edit button',
    trigger: '.o_edit_website_container > a',
},
{
    trigger: 'iframe body:not([data-hello="world"])',
    extra_trigger: '#oe_snippets.o_loaded',
    content: 'Check that the editor DOM matches its website-generic features',
    run: function () {}, // Simple check
}]});

registry.category("web_tour.tours").add('specific_website_editor', {
    test: true,
    steps: [{
    content: 'Click edit button',
    trigger: '.o_edit_website_container > a',
},
{
    trigger: 'iframe body[data-hello="world"]',
    extra_trigger: '#oe_snippets.o_loaded',
    content: 'Check that the editor DOM matches its website-specific features',
    run: function () {}, // Simple check
}]});
});
