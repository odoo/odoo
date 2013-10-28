(function () {
    'use strict';

    var website = openerp.website;
    website.menu = {};
    website.templates.push('/website/static/src/xml/website.menu.xml');

    website.menu.AddMenuDialog = website.editor.LinkDialog.extend({
        template: 'website.menu.dialog',
        make_link: function (url, new_window, label) {
        },
    });

    website.dom_ready.then(function () {
        $('.js_add_menu').on('click', function () {
            return new website.menu.AddMenuDialog().appendTo(document.body);
        });
    });

})();
