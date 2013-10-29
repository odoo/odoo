(function () {
    'use strict';

    var website = openerp.website;
    website.menu = {};
    website.add_template_file('/website/static/src/xml/website.menu.xml');

    website.menu.EditMenuDialog = website.editor.Dialog.extend({
        template: 'website.menu.dialog.edit',
        events: _.extend({}, website.editor.Dialog.prototype.events, {
            'click button.add-menu': 'add_menu',
        }),
        init: function (menu) {
            this.menu = menu;
            this.root_menu_id = menu.id;
            this.flat = this.flatenize(menu);
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
                maxLevels: 2,
                toleranceElement: '> div',
                forcePlaceholderSize: true,
                opacity: 0.6,
                placeholder: 'oe_menu_placeholder',
                tolerance: 'pointer',
                attribute: 'data-menu-id',
                expression: '()(.+)', // nestedSortable takes the second match of an expression (*sigh*)
            });
            return r;
        },
        flatenize: function (node, dict) {
            dict = dict || {};
            var self = this;
            dict[node.id] = node;
            node.children.forEach(function (child) {
                self.flatenize(child, dict);
            });
            return dict;
        },
        add_menu: function () {
            var self = this;
            var dialog = new website.menu.AddMenuDialog();
            dialog.on('add-menu', this, function (link) {
                var new_menu = {
                    id: _.uniqueId('new-'),
                    name: link[2] || link[0],
                    url: link[0],
                    new_window: link[1],
                    parent_id: false,
                    sequence: 0,
                    children: [],
                };
                self.flat[new_menu.id] = new_menu;
                self.$('.oe_menu_editor').append(
                    openerp.qweb.render(
                        'website.menu.dialog.submenu', { submenu: new_menu }));
            });
            dialog.appendTo(document.body);
        },
        save: function () {
            var self = this;
            var new_menu = this.$('.oe_menu_editor').nestedSortable('toArray', {startDepthCount: 0});
            var levels = [];
            var data = [];
            var context = website.get_context();
            // Resquence, re-tree and remove useless data
            new_menu.forEach(function (menu) {
                if (menu.item_id) {
                    levels[menu.depth] = (levels[menu.depth] || 0) + 1;
                    var mobj = self.flat[menu.item_id];
                    mobj.sequence = levels[menu.depth];
                    mobj.parent_id = (menu.parent_id|0) || menu.parent_id || self.root_menu_id;
                    delete(mobj.children);
                    delete(mobj.level);
                    data.push(mobj);
                }
            });
            openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'website.menu',
                method: 'save',
                args: [[context.website_id], data],
                kwargs: {
                    context: context
                },
            }).then(function (menu) {
                self.close();
                website.reload();
            });
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
