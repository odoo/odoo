odoo.define('website.contentMenu', function (require) {
'use strict';

var Class = require('web.Class');
var core = require('web.core');
var Dialog = require('web.Dialog');
var time = require('web.time');
var weContext = require('web_editor.context');
var weWidgets = require('web_editor.widget');
var websiteNavbarData = require('website.navbar');
var websiteRootData = require('website.WebsiteRoot');
var Widget = require('web.Widget');

var _t = core._t;
var qweb = core.qweb;

var PagePropertiesDialog = weWidgets.Dialog.extend({
    template: 'website.pagesMenu.page_info',
    xmlDependencies: weWidgets.Dialog.prototype.xmlDependencies.concat(
        ['/website/static/src/xml/website.pageProperties.xml']
    ),
    events: _.extend({}, weWidgets.Dialog.prototype.events, {
        'keyup input#page_name': '_onNameChanged',
        'keyup input#page_url': '_onUrlChanged',
        'change input#create_redirect': '_onCreateRedirectChanged',
    }),

    /**
     * @constructor
     * @override
     */
    init: function (parent, page_id, options) {
        var self = this;
        var serverUrl = window.location.origin + '/';
        var length_url = serverUrl.length;
        var serverUrlTrunc = serverUrl;
        if (length_url > 30) {
            serverUrlTrunc = serverUrl.slice(0,14) + '..' + serverUrl.slice(-14);
        }
        this.serverUrl = serverUrl;
        this.serverUrlTrunc = serverUrlTrunc;
        this.current_page_url = window.location.pathname;
        this.page_id = page_id;

        var buttons = [
            {text: _t("Save"), classes: 'btn-primary', click: this.save},
            {text: _t("Discard"), close: true},
        ];
        if (options.fromPageManagement) {
            buttons.push({
                text: _t("Go To Page"),
                icon: 'fa-globe',
                classes: 'btn-link float-right',
                click: function (e) {
                    window.location.href = '/' + self.page.url;
                },
            });
        }
        buttons.push({
            text: _t("Delete Page"),
            icon: 'fa-trash',
            classes: 'btn-link float-right',
            click: function (e) {
                _deletePage.call(this, self.page_id, options.fromPageManagement);
            },
        });
        this._super(parent, _.extend({}, {
            title: _t("Page Properties"),
            size: 'medium',
            buttons: buttons,
        }, options || {}));
    },
    /**
     * @override
     */
    willStart: function () {
        var defs = [this._super.apply(this, arguments)];
        var self = this;

        defs.push(this._rpc({
            model: 'website.page',
            method: 'get_page_info',
            args: [this.page_id],
        }).then(function (page) {
            page[0].url = _.str.startsWith(page[0].url, '/') ? page[0].url.substring(1) : page[0].url;
            self.page = page[0];
        }));

        defs.push(this._rpc({
            model: 'website.redirect',
            method: 'fields_get',
        }).then(function (fields) {
            self.fields = fields;
        }));

        return $.when.apply($, defs);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;

        var defs = [this._super.apply(this, arguments)];

        this.$('.ask_for_redirect').addClass('d-none');
        this.$('.redirect_type').addClass('d-none');
        this.$('.warn_about_call').addClass('d-none');

        defs.push(this._getPageDependencies(this.page_id)
        .then(function (dependencies) {
            var dep_text = [];
            _.each(dependencies, function (value, index) {
                if (value.length > 0) {
                    dep_text.push(value.length + ' ' + index.toLowerCase());
                }
            });
            dep_text = dep_text.join(', ');
            self.$('#dependencies_redirect').html(qweb.render('website.show_page_dependencies', { dependencies: dependencies, dep_text: dep_text }));
            self.$('#dependencies_redirect [data-toggle="popover"]').popover({
                container: 'body',
            });
        }));

        defs.push(this._getSupportedMimetype()
        .then(function (mimetypes) {
            self.supportedMimetype = mimetypes;
        }));

        defs.push(this._getPageKeyDependencies(this.page_id)
        .then(function (dependencies) {
            var dep_text = [];
            _.each(dependencies, function (value, index) {
                if (value.length > 0) {
                    dep_text.push(value.length + ' ' + index.toLowerCase());
                }
            });
            dep_text = dep_text.join(', ');
            self.$('.warn_about_call').html(qweb.render('website.show_page_key_dependencies', {dependencies: dependencies, dep_text: dep_text}));
            self.$('.warn_about_call [data-toggle="popover"]').popover({
               container: 'body',
            });
        }));

        defs.push(this._rpc({model: 'res.users',
                             method: 'has_group',
                             args: ['website.group_multi_website']})
                  .then(function (has_group) {
                      if (!has_group) {
                          self.$('#website_restriction').addClass('hidden');
                      }
                  }));

        var datepickersOptions = {
            minDate: moment({y: 1900}),
            maxDate: moment().add(200, 'y'),
            calendarWeeks: true,
            icons : {
                time: 'fa fa-clock-o',
                date: 'fa fa-calendar',
                next: 'fa fa-chevron-right',
                previous: 'fa fa-chevron-left',
                up: 'fa fa-chevron-up',
                down: 'fa fa-chevron-down',
            },
            locale : moment.locale(),
            format : time.getLangDatetimeFormat(),
            widgetPositioning : {
                horizontal: 'auto',
                vertical: 'top',
            },
             widgetParent: 'body',
        };
        if (this.page.date_publish) {
            datepickersOptions.defaultDate = time.str_to_datetime(this.page.date_publish);
        }
        this.$('#date_publish_container').datetimepicker(datepickersOptions);

        return $.when.apply($, defs);
    },
    /**
     * @override
     */
    destroy: function () {
        $('.popover').popover('hide');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    save: function (data) {
        var self = this;
        var context = weContext.get();
        var url = this.$('#page_url').val();

        var $date_publish = this.$("#date_publish");
        $date_publish.closest(".form-group").removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
        var date_publish = $date_publish.val();
        if (date_publish !== "") {
            date_publish = this._parse_date(date_publish);
            if (!date_publish) {
                $date_publish.closest(".form-group").addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
                return;
            }
        }
        var params = {
            id: this.page.id,
            name: this.$('#page_name').val(),
            // Replace duplicate following '/' by only one '/'
            url: url.replace(/\/{2,}/g, '/'),
            is_menu: this.$('#is_menu').prop('checked'),
            is_homepage: this.$('#is_homepage').prop('checked'),
            website_published: this.$('#is_published').prop('checked'),
            create_redirect: this.$('#create_redirect').prop('checked'),
            redirect_type: this.$('#redirect_type').val(),
            website_indexed: this.$('#is_indexed').prop('checked'),
            date_publish: date_publish,
        };
        this._rpc({
            model: 'website.page',
            method: 'save_page_info',
            args: [[context.website_id], params],
        }).then(function (url) {
            // If from page manager: reload url, if from page itself: go to
            // (possibly) new url
            var mo;
            self.trigger_up('main_object_request', {
                callback: function (value) {
                    mo = value;
                },
            });
            if (mo.model === 'website.page') {
                window.location.href = url.toLowerCase();
            } else {
                window.location.reload(true);
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Retrieves the page URL dependencies for the given object id.
     *
     * @private
     * @param {integer} moID
     * @returns {Deferred<Array>}
     */
    _getPageDependencies: function (moID) {
        return this._rpc({
            model: 'website',
            method: 'page_search_dependencies',
            args: [moID],
        });
    },
    /**
     * Retrieves the page's key dependencies for the given object id.
     *
     * @private
     * @param {integer} moID
     * @returns {Deferred<Array>}
     */
    _getPageKeyDependencies: function (moID) {
        return this._rpc({
            model: 'website',
            method: 'page_search_key_dependencies',
            args: [moID],
        });
    },
    /**
     * Retrieves supported mimtype
     *
     * @private
     * @returns {Deferred<Array>}
     */
    _getSupportedMimetype: function () {
        return this._rpc({
            model: 'website',
            method: 'guess_mimetype',
        });
    },
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
     * Converts a string representing the browser datetime
     * (exemple: Albanian: '2018-Qer-22 15.12.35.')
     * to a string representing UTC in Odoo's datetime string format
     * (exemple: '2018-04-22 13:12:35').
     *
     * The time zone of the datetime string is assumed to be the one of the
     * browser and it will be converted to UTC (standard for Odoo).
     *
     * @private
     * @param {String} value A string representing a datetime.
     * @returns {String|false} A string representing an UTC datetime if the given value is valid, false otherwise.
     */
    _parse_date: function (value) {
        var datetime = moment(value, time.getLangDatetimeFormat(), true);
        if (datetime.isValid()) {
            return time.datetime_to_str(datetime.toDate());
        }
        else {
            return false;
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onUrlChanged: function () {
        var url = this.$('input#page_url').val();
        this.$('.ask_for_redirect').toggleClass('d-none', url === this.page.url);
    },
    /**
     * @private
     */
    _onNameChanged: function () {
        var name = this.$('input#page_name').val();
        // If the file type is a supported mimetype, check if it is t-called.
        // If so, warn user. Note: different from page_search_dependencies which
        // check only for url and not key
        var ext = '.' + this.page.name.split('.').pop();
        if (ext in this.supportedMimetype && ext !== '.html') {
            this.$('.warn_about_call').toggleClass('d-none', name === this.page.name);
        }
    },
    /**
     * @private
     */
    _onCreateRedirectChanged: function () {
        var createRedirect = this.$('input#create_redirect').prop('checked');
        this.$('.redirect_type').toggleClass('d-none', !createRedirect);
    },
});

var MenuEntryDialog = weWidgets.LinkDialog.extend({
    xmlDependencies: weWidgets.LinkDialog.prototype.xmlDependencies.concat(
        ['/website/static/src/xml/website.contentMenu.xml']
    ),

    /**
     * @constructor
     */
    init: function (parent, options, editor, data) {
        data.text = data.name || '';
        data.isNewWindow = data.new_window;
        this.data = data;
        this._super(parent, _.extend({}, {
            title: _t("Create Menu"),
        }, options || {}), editor, data);
    },
    /**
     * @override
     */
    start: function () {
        // Remove style related elements
        this.$('.o_link_dialog_preview').remove();
        this.$('input[name="is_new_window"], .link-style').closest('.form-group').remove();
        this.$modal.find('.modal-lg').removeClass('modal-lg');
        this.$('form.col-lg-8').removeClass('col-lg-8').addClass('col-12');

        // Adapt URL label
        this.$('label[for="o_link_dialog_label_input"]').text(_t("Menu Label"));

        this.$('#o_link_dialog_url_input').after(qweb.render('website.contentMenu.dialog.edit.link_menu_hint'));

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    save: function () {
        var $e = this.$('#o_link_dialog_label_input');
        if (!$e.val() || !$e[0].checkValidity()) {
            $e.closest('.form-group').addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid')
            $e.focus();
            return;
        }
        return this._super.apply(this, arguments);
    },

});

var SelectEditMenuDialog = weWidgets.Dialog.extend({
    template: 'website.contentMenu.dialog.select',
    xmlDependencies: weWidgets.Dialog.prototype.xmlDependencies.concat(
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

var EditMenuDialog = weWidgets.Dialog.extend({
    template: 'website.contentMenu.dialog.edit',
    xmlDependencies: weWidgets.Dialog.prototype.xmlDependencies.concat(
        ['/website/static/src/xml/website.contentMenu.xml']
    ),
    events: _.extend({}, weWidgets.Dialog.prototype.events, {
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
            args: [context.website_id, { data: data, to_delete: self.to_delete }],
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
        var dialog = new MenuEntryDialog(this, {}, undefined, {});
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

var PageOption = Class.extend({
    /**
     * @constructor
     * @param {string} name
     *        the option's name = the field's name in website.page model
     * @param {*} value
     * @param {function} setValueCallback
     *        a function which simulates an option's value change without
     *        asking the server to change it
     */
    init: function (name, value, setValueCallback) {
        this.name = name;
        this.value = value;
        this.isDirty = false;
        this.setValueCallback = setValueCallback;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Sets the new option's value thanks to the related callback.
     *
     * @param {*} [value]
     *        by default: consider the current value is a boolean and toggle it
     */
    setValue: function (value) {
        if (value === undefined) {
            value = !this.value;
        }
        this.setValueCallback.call(this, value);
        this.value = value;
        this.isDirty = true;
    },
});

var ContentMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    xmlDependencies: ['/website/static/src/xml/website.xml'],
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions || {}, {
        edit_menu: '_editMenu',
        get_page_option: '_getPageOption',
        on_save: '_onSave',
        page_properties: '_pageProperties',
        toggle_page_option: '_togglePageOption',
    }),
    pageOptionsSetValueCallbacks: {
        header_overlay: function (value) {
            $('#wrapwrap').toggleClass('o_header_overlay', value);
        },
        header_color: function (value) {
            $('#wrapwrap > header').removeClass(this.value)
                                   .addClass(value);
        },
    },

    /**
     * @override
     */
    start: function () {
        var self = this;
        this.pageOptions = {};
        _.each($('.o_page_option_data'), function (el) {
            var value = el.value;
            if (value === "True") {
                value = true;
            } else if (value === "False") {
                value = false;
            }
            self.pageOptions[el.name] = new PageOption(
                el.name,
                value,
                self.pageOptionsSetValueCallbacks[el.name]
            );
        });
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

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
     * Retrieves the value of a page option.
     *
     * @private
     * @param {string} name
     * @returns {Deferred<*>}
     */
    _getPageOption: function (name) {
        var option = this.pageOptions[name];
        if (!option) {
            return $.Deferred().reject();
        }
        return $.when(option.value);
    },
    /**
     * On save, simulated page options have to be server-saved.
     *
     * @private
     * @returns {Deferred}
     */
    _onSave: function () {
        var self = this;
        var defs = _.map(this.pageOptions, function (option, optionName) {
            if (option.isDirty) {
                return self._togglePageOption({
                    name: optionName,
                    value: option.value,
                }, true, true);
            }
        });
        return $.when.apply($, defs);
    },
    /**
     * Opens the page properties dialog.
     *
     * @private
     * @returns {Deferred}
     */
    _pageProperties: function () {
        var mo;
        this.trigger_up('main_object_request', {
            callback: function (value) {
                mo = value;
            },
        });
        var dialog = new PagePropertiesDialog(this, mo.id, {}).open();
        return dialog.opened();
    },
    /**
     * Toggles a page option.
     *
     * @private
     * @param {Object} params
     * @param {string} params.name
     * @param {*} [params.value] (change value by default true -> false -> true)
     * @param {boolean} [forceSave=false]
     * @param {boolean} [noReload=false]
     * @returns {Deferred}
     */
    _togglePageOption: function (params, forceSave, noReload) {
        // First check it is a website page
        var mo;
        this.trigger_up('main_object_request', {
            callback: function (value) {
                mo = value;
            },
        });
        if (mo.model !== 'website.page') {
            return $.Deferred().reject();
        }

        // Check if this is a valid option
        var option = this.pageOptions[params.name];
        if (!option) {
            return $.Deferred().reject();
        }

        // Toggle the value
        option.setValue(params.value);

        // If simulate is true, it means we want the option to be toggled but
        // not saved on the server yet
        if (!forceSave) {
            return $.when();
        }

        // If not, write on the server page and reload the current location
        var vals = {};
        vals[params.name] = option.value;
        var def = this._rpc({
            model: 'website.page',
            method: 'write',
            args: [[mo.id], vals],
        });
        if (noReload) {
            return def;
        }
        return def.then(function () {
            window.location.reload();
            return $.Deferred();
        });
    },
});

var PageManagement = Widget.extend({
    xmlDependencies: ['/website/static/src/xml/website.xml'],
    events: {
        'click a.js_page_properties': '_onPagePropertiesButtonClick',
        'click a.js_clone_page': '_onClonePageButtonClick',
        'click a.js_delete_page': '_onDeletePageButtonClick',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Retrieves the page dependencies for the given object id.
     *
     * @private
     * @param {integer} moID
     * @returns {Deferred<Array>}
     */
    _getPageDependencies: function (moID) {
        return this._rpc({
            model: 'website',
            method: 'page_search_dependencies',
            args: [moID],
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onPagePropertiesButtonClick: function (ev) {
        var moID = $(ev.currentTarget).data('id');
        var dialog = new PagePropertiesDialog(this,moID, {'fromPageManagement': true}).open();
        return dialog;
    },
    _onClonePageButtonClick: function (ev) {
        var pageId = $(ev.currentTarget).data('id');
        this._rpc({
            model: 'website.page',
            method: 'clone_page',
            args: [pageId],
        }).then(function (path) {
            window.location.href = path;
        });
    },
    _onDeletePageButtonClick: function (ev) {
        var pageId = $(ev.currentTarget).data('id');
        _deletePage.call(this, pageId, true);
    },
});

/**
 * Deletes the page after showing a dependencies warning for the given page id.
 *
 * @private
 * @param {integer} pageId - The ID of the page to be deleted
 * @param {Boolean} fromPageManagement
 *                  Is the function called by the page manager?
 *                  It will affect redirect after page deletion: reload or '/'
 */
// TODO: This function should be integrated in a widget in the future
function _deletePage(pageId, fromPageManagement) {
    var self = this;
    var def = $.Deferred();

    // Search the page dependencies
    this._getPageDependencies(pageId)
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
            model: 'website.page',
            method: 'unlink',
            args: [pageId],
        });
    }).then(function () {
        if (fromPageManagement) {
            window.location.reload(true);
        }
        else {
            window.location.href = '/';
        }
    }, def.reject.bind(def));
}

websiteNavbarData.websiteNavbarRegistry.add(ContentMenu, '#content-menu');
websiteRootData.websiteRootRegistry.add(PageManagement, '#list_website_pages');

return {
    PagePropertiesDialog: PagePropertiesDialog,
    ContentMenu: ContentMenu,
    EditMenuDialog: EditMenuDialog,
    MenuEntryDialog: MenuEntryDialog,
    SelectEditMenuDialog: SelectEditMenuDialog,
};
});
