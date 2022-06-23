odoo.define('website.tour.specific_website_editor', function (require) {
'use strict';

const tour = require('web_tour.tour');

tour.register('generic_website_editor', {
    test: true,
}, [{
    trigger: 'a.o_frontend_to_backend_edit_btn',
    content: 'Go to backend',
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
    trigger: 'a.o_frontend_to_backend_edit_btn',
    content: 'Go to backend',
},
{
    trigger: 'iframe body[data-hello="world"]',
    extra_trigger: '#oe_snippets.o_loaded',
    content: 'Check that the editor DOM matches its website-specific features',
    run: function () {}, // Simple check
}]);
});
