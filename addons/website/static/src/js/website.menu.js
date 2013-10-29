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
        $("#top_menu").sortable({
            group: 'nav',
            nested: true,
            vertical: false,
            exclude: '.divider',
            onDragStart: function($item, container, _super) {
                $item.find('ul.dropdown-menu').sortable('disable');
                _super($item, container);
            },
            onDrop: function($item, container, _super) {
                $item.find('ul.dropdown-menu').sortable('enable');
                _super($item, container);
            }
        });
        $("ul.dropdown-menu").sortable({
            group: 'nav'
        });
    });

})();
