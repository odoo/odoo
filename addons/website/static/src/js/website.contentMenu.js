(function () {
    'use strict';

    var website = openerp.website;
    website.contentMenu = {};
    website.add_template_file('/website/static/src/xml/website.contentMenu.xml');
    var _t = openerp._t;

    website.EditorBarContent = openerp.Widget.extend({
        start: function() {
            var self = this;
            self.$el.on('click', 'a', function(ev) {
                ev.preventDefault();
                var $content_item = $(this);
                self[$content_item.data('action')]();
            })
            
            return this._super();
        },
        edit_menu: function() {
            var self = this;
            var context = website.get_context();
            openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'website.menu',
                method: 'get_tree',
                args: [context.website_id],
                kwargs: {
                    context: context
                },
            }).then(function (menu) {
                var result = new website.contentMenu.EditMenuDialog(menu).appendTo(document.body);
                return result;
            });
        },
        new_page: function() {
            website.prompt({
                id: "editor_new_page",
                window_title: _t("New Page"),
                input: _t("Page Title"),
                init: function () {
                    var $group = this.$dialog.find("div.form-group");
                    $group.removeClass("mb0");

                    var $add = $(
                        '<div class="form-group mb0">'+
                            '<label class="col-sm-offset-3 col-sm-9 text-left">'+
                            '    <input type="checkbox" checked="checked" required="required"/> '+
                            '</label>'+
                        '</div>');
                    $add.find('label').append(_t("Add page in menu"));
                    $group.after($add);
                }
            }).then(function (val, field, $dialog) {
                if (val) {
                    var url = '/website/add/' + encodeURIComponent(val);
                    if ($dialog.find('input[type="checkbox"]').is(':checked')) url +="?add_menu=1";
                    document.location = url;
                }
            });
        }
    });

    website.contentMenu.EditMenuDialog = website.editor.Dialog.extend({
        template: 'website.contentMenu.dialog.edit',
        events: _.extend({}, website.editor.Dialog.prototype.events, {
            'click a.js_add_menu': 'add_menu',
            'click button.js_edit_menu': 'edit_menu',
            'click button.js_delete_menu': 'delete_menu',
        }),
        init: function (menu) {
            this.menu = menu;
            this.root_menu_id = menu.id;
            this.flat = this.flatenize(menu);
            this.to_delete = [];
            this._super();
        },
        start: function () {
            var r = this._super.apply(this, arguments);
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
            var dialog = new website.contentMenu.MenuEntryDialog();
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
                    openerp.qweb.render('website.contentMenu.dialog.submenu', { submenu: new_menu }));
            });
            dialog.appendTo(document.body);
        },
        edit_menu: function (ev) {
            var self = this;
            var menu_id = $(ev.currentTarget).closest('[data-menu-id]').data('menu-id');
            var menu = self.flat[menu_id];
            if (menu) {
                var dialog = new website.contentMenu.MenuEntryDialog(undefined, menu);
                dialog.on('update-menu', this, function (link) {
                    var id = link.shift();
                    var menu_obj = self.flat[id];
                    _.extend(menu_obj, {
                        name: link[2],
                        url: link[0],
                        new_window: link[1],
                    });
                    var $menu = self.$('[data-menu-id="' + id + '"]');
                    $menu.find('.js_menu_label').first().text(menu_obj.name);
                });
                dialog.appendTo(document.body);
            } else {
                alert("Could not find menu entry");
            }
        },
        delete_menu: function (ev) {
            var self = this;
            var $menu = $(ev.currentTarget).closest('[data-menu-id]');
            var mid = $menu.data('menu-id')|0;
            if (mid) {
                this.to_delete.push(mid);
            }
            $menu.remove();
        },
        save: function () {
            var self = this;
            var new_menu = this.$('.oe_menu_editor').nestedSortable('toArray', {startDepthCount: 0});
            var levels = [];
            var data = [];
            var context = website.get_context();
            // Resequence, re-tree and remove useless data
            new_menu.forEach(function (menu) {
                if (menu.item_id) {
                    levels[menu.depth] = (levels[menu.depth] || 0) + 1;
                    var mobj = self.flat[menu.item_id];
                    mobj.sequence = levels[menu.depth];
                    mobj.parent_id = (menu.parent_id|0) || menu.parent_id || self.root_menu_id;
                    delete(mobj.children);
                    data.push(mobj);
                }
            });
            openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'website.menu',
                method: 'save',
                args: [[context.website_id], { data: data, to_delete: self.to_delete }],
                kwargs: {
                    context: context
                },
            }).then(function (menu) {
                self.close();
                website.reload();
            });
        },
    });

    website.contentMenu.MenuEntryDialog = website.editor.LinkDialog.extend({
        template: 'website.contentMenu.dialog.add',
        init: function (editor, data) {
            this.data = data;
            return this._super.apply(this, arguments);
        },
        start: function () {
            var self = this;
            var result = $.when(this._super.apply(this, arguments)).then(function () {
                if (self.data) {
                    self.bind_data(self.data.name, self.data.url, self.data.new_window);
                }
                var $link_text = self.$('#link-text').focus();
                self.$('#link-page').change(function (e) {
                    if ($link_text.val()) { return; }
                    var data = $(this).select2('data');
                    $link_text.val(data.create ? data.id : data.text);
                    $link_text.focus();
                });
            });
            return result;
        },
        save: function () {
            var $e = this.$('#link-text');
            if (!$e.val() || !$e[0].checkValidity()) {
                $e.closest('.form-group').addClass('has-error');
                $e.focus();
                return;
            }
            return this._super.apply(this, arguments);
        },
        make_link: function (url, new_window, label) {
            var menu_label = this.$('input#link-text').val() || label;
            if (this.data) {
                this.trigger('update-menu', [this.data.id, url, new_window, menu_label]);
            } else {
                this.trigger('add-menu', [url, new_window, menu_label]);
            }
        },
        destroy: function () {
            this._super.apply(this, arguments);
        },
    });

    $(document).ready(function() {
        var content = new website.EditorBarContent();
        content.setElement($('.oe_content_menu'));
        content.start();
    });

})();
