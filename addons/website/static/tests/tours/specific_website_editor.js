odoo.define('website.tour.specific_website_editor', function (require) {
'use strict';

const tour = require('web_tour.tour');

tour.register('generic_website_editor', {
    test: true,
}, [{
    content: 'Click edit button',
    trigger: '.o_edit_website_container > a',
},
{
    trigger: 'iframe body:not([data-hello="world"])',
    extra_trigger: '#oe_snippets.o_loaded',
    content: 'Check that the editor DOM matches its website-generic features',
    run: function () {}, // Simple check
}]);

tour.register('specific_website_editor', {
    test: true,
}, [{
    content: 'Click edit button',
    trigger: '.o_edit_website_container > a',
},
{
    trigger: 'iframe body[data-hello="world"]',
    extra_trigger: '#oe_snippets.o_loaded',
    content: 'Check that the editor DOM matches its website-specific features',
    run: function () {}, // Simple check
}]);
});
