(function () {
    'use strict';

    var website = openerp.website;
    website.menu = {};
    website.templates.push('/website/static/src/xml/website.menu.xml');

    website.menu.EditMenuDialog = website.editor.Dialog.extend({
        template: 'website.menu.dialog.edit',
        events: _.extend({}, website.editor.Dialog.prototype.events, {
            'click button.add-menu': 'add_menu',
        }),
        init: function (menu) {
            this.menu = menu;
            this._super();
        },
        start: function () {
            var r = this._super.apply(this, arguments);
            var button = openerp.qweb.render('website.menu.dialog.footer-button');
            this.$('.modal-footer').prepend(button);
            this.$('.oe_menu_editor').nestedSortable({
                listType: 'ul',
                handle: 'div',
                items: 'li',
                toleranceElement: '> div',
                forcePlaceholderSize: true,
                opacity: 0.6,
                placeholder: 'oe_menu_placeholder',
                tolerance: 'pointer',
            });
            return r;
        },
        add_menu: function () {
            var self = this;
            var dialog = new website.menu.AddMenuDialog();
            dialog.on('add-menu', this, function (link) {
                var context = {
                    submenu: {
                        name: link[2] || link[0],
                        new_window: link[1],
                        url: link[0],
                        children: [],
                    },
                };
                self.$('.oe_menu_editor').append(
                    openerp.qweb.render(
                        'website.menu.dialog.submenu', context));
            });
            dialog.appendTo(document.body);
        },
        save: function () {
            debugger
        },
    });

    website.menu.AddMenuDialog = website.editor.LinkDialog.extend({
        template: 'website.menu.dialog.add',
        make_link: function (url, new_window, label) {
            this.trigger('add-menu', [url, new_window, label]);
        },
    });

    website.dom_ready.then(function () {
        $('.js_edit_menu').on('click', function () {
            var context = website.get_context();
            openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'website.menu',
                method: 'get_tree',
                args: [[context.website_id]],
                kwargs: {
                    context: context
                },
            }).then(function (menu) {
                return new website.menu.EditMenuDialog(menu).appendTo(document.body);
            });
        });
    });

})();
