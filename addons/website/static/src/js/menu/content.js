odoo.define('website.contentMenu', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var weContext = require('web_editor.context');
var widget = require('web_editor.widget');
var websiteNavbarData = require('website.navbar');

var _t = core._t;
var qweb = core.qweb;

var MenuEntryDialog = widget.LinkDialog.extend({
    xmlDependencies: widget.LinkDialog.prototype.xmlDependencies.concat(
        ['/website/static/src/xml/website.contentMenu.xml']
    ),

    /**
     * @constructor
     * @override
     */
    init: function (parent, options, editor, data) {
        data.text = data.name || '';
        data.isNewWindow = data.new_window;
        this.data = data;
        this.menu_link_options = options.menu_link_options;
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.$('.o_link_dialog_preview').remove();
        this.$('.window-new, .link-style').closest('.form-group').remove();
        this.$('label[for="o_link_dialog_label_input"]').text(_t("Menu Label"));
        if (this.menu_link_options) { // add menu link option only when adding new menu
            this.$('#o_link_dialog_label_input').closest('.form-group').after(qweb.render('website.contentMenu.dialog.edit.link_menu_options'));
            this.$('input[name=link_menu_options]').on('change', function () {
                self.$('#o_link_dialog_url_input').closest('.form-group').toggle();
            });
        }
        this.$modal.find('.modal-lg').removeClass('modal-lg')
                   .find('.col-md-8').removeClass('col-md-8').addClass('col-xs-12');
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    save: function () {
        var $e = this.$('#o_link_dialog_label_input');
        if (!$e.val() || !$e[0].checkValidity()) {
            $e.closest('.form-group').addClass('has-error');
            $e.focus();
            return;
        }
        if (this.$('input[name=link_menu_options]:checked').val() === 'new_page') {
            window.location = '/website/add/' + encodeURIComponent($e.val()) + '?add_menu=1';
            return;
        }
        return this._super.apply(this, arguments);
    },
});

var SelectEditMenuDialog = widget.Dialog.extend({
    template: 'website.contentMenu.dialog.select',
    xmlDependencies: widget.Dialog.prototype.xmlDependencies.concat(
        ['/website/static/src/xml/website.contentMenu.xml']
    ),

    /**
     * @constructor
     * @override
     */
    init: function (parent, options) {
        var self = this;
        self.roots = [{id: null, name: _t("Top Menu")}];
        $('[data-content_menu_id]').each(function () {
            self.roots.push({id: $(this).data('content_menu_id'), name: $(this).attr('name')});
        });
        this._super(parent, _.extend({}, {
            title: _t("Select a Menu"),
            save_text: _t("Continue")
        }, options || {}));
    },
    /**
     * @override
     */
    save: function () {
        this.final_data = parseInt(this.$el.find('select').val() || null);
        this._super.apply(this, arguments);
    },
});

var EditMenuDialog = widget.Dialog.extend({
    template: 'website.contentMenu.dialog.edit',
    xmlDependencies: widget.Dialog.prototype.xmlDependencies.concat(
        ['/website/static/src/xml/website.contentMenu.xml']
    ),
    events: _.extend({}, widget.Dialog.prototype.events, {
        'click a.js_add_menu': '_onAddMenuButtonClick',
        'click button.js_delete_menu': '_onDeleteMenuButtonClick',
        'click button.js_edit_menu': '_onEditMenuButtonClick',
    }),

    /**
     * @constructor
     * @override
     */
    init: function (parent, options, rootID) {
        this._super(parent, _.extend({}, {
            title: _t("Edit Menu"),
            size: 'medium',
        }, options || {}));
        this.rootID = rootID;
    },
    /**
     * @override
     */
    willStart: function () {
        var defs = [this._super.apply(this, arguments)];
        var self = this;
        var context = weContext.get();
        defs.push(this._rpc({
            model: 'website.menu',
            method: 'get_tree',
            args: [context.website_id, this.rootID],
            context: context,
        }).then(function (menu) {
            self.menu = menu;
            self.root_menu_id = menu.id;
            self.flat = self._flatenize(menu);
            self.to_delete = [];
        }));
        return $.when.apply($, defs);
    },
    /**
     * @override
     */
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

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    save: function () {
        var _super = this._super.bind(this);
        var self = this;
        var new_menu = this.$('.oe_menu_editor').nestedSortable('toArray', {startDepthCount: 0});
        var levels = [];
        var data = [];
        var context = weContext.get();
        // Resequence, re-tree and remove useless data
        new_menu.forEach(function (menu) {
            if (menu.id) {
                levels[menu.depth] = (levels[menu.depth] || 0) + 1;
                var mobj = self.flat[menu.id];
                mobj.sequence = levels[menu.depth];
                mobj.parent_id = (menu.parent_id|0) || menu.parent_id || self.root_menu_id;
                delete(mobj.children);
                data.push(mobj);
            }
        });
        this._rpc({
            model: 'website.menu',
            method: 'save',
            args: [[context.website_id], { data: data, to_delete: self.to_delete }],
            context: context,
        }).then(function () {
            return _super();
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns a mapping id -> menu item containing all the menu items in the
     * given menu hierarchy.
     *
     * @private
     * @param {Object} node
     * @param {Object} [_dict] internal use: the mapping being built
     * @returns {Object}
     */
    _flatenize: function (node, _dict) {
        _dict = _dict || {};
        var self = this;
        _dict[node.id] = node;
        node.children.forEach(function (child) {
            self._flatenize(child, _dict);
        });
        return _dict;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the "add menu" button is clicked -> Opens the appropriate
     * dialog to edit this new menu.
     *
     * @private
     */
    _onAddMenuButtonClick: function () {
        var self = this;
        var dialog = new MenuEntryDialog(this, {menu_link_options: true}, undefined, {});
        dialog.on('save', this, function (link) {
            var new_menu = {
                id: _.uniqueId('new-'),
                name: link.text,
                url: link.url,
                new_window: link.isNewWindow,
                parent_id: false,
                sequence: 0,
                children: [],
            };
            self.flat[new_menu.id] = new_menu;
            self.$('.oe_menu_editor').append(
                qweb.render('website.contentMenu.dialog.submenu', { submenu: new_menu }));
        });
        dialog.open();
    },
    /**
     * Called when the "delete menu" button is clicked -> Deletes this menu.
     *
     * @private
     */
    _onDeleteMenuButtonClick: function (ev) {
        var $menu = $(ev.currentTarget).closest('[data-menu-id]');
        var menuID = $menu.data('menu-id')|0;
        if (menuID) {
            this.to_delete.push(menuID);
        }
        $menu.remove();
    },
    /**
     * Called when the "edit menu" button is clicked -> Opens the appropriate
     * dialog to edit this menu.
     *
     * @private
     */
    _onEditMenuButtonClick: function (ev) {
        var self = this;
        var menu_id = $(ev.currentTarget).closest('[data-menu-id]').data('menu-id');
        var menu = self.flat[menu_id];
        if (menu) {
            var dialog = new MenuEntryDialog(this, {}, undefined, menu);
            dialog.on('save', this, function (link) {
                var id = link.id;
                var menu_obj = self.flat[id];
                _.extend(menu_obj, {
                    'name': link.text,
                    'url': link.url,
                    'new_window': link.isNewWindow,
                });
                var $menu = self.$('[data-menu-id="' + id + '"]');
                $menu.find('.js_menu_label').first().text(menu_obj.name);
            });
            dialog.open();
        } else {
            Dialog.alert(null, "Could not find menu entry");
        }
    },
});

var ContentMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    xmlDependencies: ['/website/static/src/xml/website.xml'],
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions || {}, {
        delete_page: '_deletePage',
        edit_menu: '_editMenu',
        rename_page: '_renamePage',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns information about the page main object.
     *
     * @private
     * @returns {Object} model and id
     */
    _getMainObject: function () {
        var repr = $('html').data('main-object');
        var m = repr.match(/(.+)\((\d+),(.*)\)/);
        return {
            model: m[1],
            id: m[2] | 0,
        };
    },
    /**
     * Retrieves the page dependencies for the given object id.
     *
     * @private
     * @param {integer} moID
     * @param {Object} context
     * @returns {Deferred<Array>}
     */
    _getPageDependencies: function (moID, context) {
        return this._rpc({
            model: 'website',
            method: 'page_search_dependencies',
            args: [moID],
            context: context,
        });
    },

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Searches for the page dependencies, inform the user about them then
     * delete the page if the user agrees.
     *
     * @private
     * @returns {Deferred}
     */
    _deletePage: function () {
        var self = this;
        var moID = self._getMainObject().id;
        var context = weContext.get();

        var def = $.Deferred();

        // Search the page dependencies
        this._getPageDependencies(moID, context)
        .then(function (dependencies) {
        // Inform the user about those dependencies and ask him confirmation
            var confirmDef = $.Deferred();
            Dialog.safeConfirm(self, "", {
                title: _t("Delete Page"),
                $content: $(qweb.render('website.delete_page', {dependencies: dependencies})),
                confirm_callback: confirmDef.resolve.bind(confirmDef),
                cancel_callback: def.resolve.bind(self),
            });
            return confirmDef;
        }).then(function () {
        // Delete the page if the user confirmed
            return self._rpc({
                model: 'website',
                method: 'delete_page',
                args: [moID],
                context: context,
            });
        }).then(function () {
        // Redirect to homepage as the page is now deleted
            window.location.href = '/';
        }, def.reject.bind(def));

        return def;
    },
    /**
     * Asks the user which menu to edit if multiple menus exist on the page.
     * Then opens the menu edition dialog.
     * Then executes the given callback once the edition is saved, to finally
     * reload the page.
     *
     * @private
     * @param {function} [beforeReloadCallback]
     * @returns {Deferred}
     *          Unresolved if the menu is edited and saved as the page will be
     *          reloaded.
     *          Resolved otherwise.
     */
    _editMenu: function (beforeReloadCallback) {
        var self = this;
        var def = $.Deferred();

        // If there is multiple menu on the page, ask the user which one he
        // wants to edit
        var selectDef = $.Deferred();
        if ($('[data-content_menu_id]').length) {
            var select = new SelectEditMenuDialog(this);
            select.on('save', selectDef, selectDef.resolve);
            select.on('cancel', def, def.resolve);
            select.open();
        } else {
            selectDef.resolve(null);
        }
        selectDef.then(function (rootID) {
            // Open the dialog to show the menu structure and allow its edition
            var editDef = $.Deferred();
            var dialog = new EditMenuDialog(self, {}, rootID).open();
            dialog.on('save', editDef, editDef.resolve);
            dialog.on('cancel', def, def.resolve);
            return editDef;
        }).then(function () {
            // Before reloading the page after menu modification, does the
            // given action to do.
            return beforeReloadCallback && beforeReloadCallback();
        }).then(function () {
            // Reload the page so that the menu modification are shown
            window.location.reload(true);
        });

        return def;
    },
    /**
     * Asks the user for the new name of the page, then reloads to the new page
     * with the correct name if saved.
     *
     * @private
     * @returns {Deferred}
     *          Unresolved if the page's name is changed and saved as the page
     *          will be reloaded.
     *          Resolved otherwise.
     */
    _renamePage: function () {
        var def = $.Deferred();

        var self = this;
        var moID = self._getMainObject().id;
        var context = weContext.get();

        // Search the page dependencies
        this._getPageDependencies(moID, context).then(function (dependencies) {
            // Ask the user for the new page name and inform him about the dependencies
            var renameDef = $.Deferred();
            var $content = $(qweb.render('website.rename_page', {dependencies: dependencies}));
            Dialog.confirm(self, "", {
                title: _t("Rename This Page"),
                $content: $content,
                confirm_callback: function () {
                    var $newNameInput = $content.find('input#new_name');
                    renameDef.resolve($newNameInput.val());
                },
                cancel_callback: def.resolve.bind(def),
            });
            return renameDef;
        }).then(function (newName) {
            // Rename the page with the user's choice
            return self._rpc({
                model: 'website',
                method: 'rename_page',
                args: [moID, newName],
                context: context,
            });
        }).then(function (newTechnicalName) {
            // Redirects to the new renamed page
            window.location.href = ('/page/' + encodeURIComponent(newTechnicalName));
        }, def.reject.bind(def));

        return def;
    },
});

websiteNavbarData.websiteNavbarRegistry.add(ContentMenu, '#content-menu');

return {
    ContentMenu: ContentMenu,
    EditMenuDialog: EditMenuDialog,
    MenuEntryDialog: MenuEntryDialog,
    SelectEditMenuDialog: SelectEditMenuDialog,
};
});
