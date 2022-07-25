/** @odoo-module alias=website.contentMenu */

import Class from 'web.Class';
import core from 'web.core';
import Dialog from 'web.Dialog';
import time from 'web.time';
import weWidgets from 'wysiwyg.widgets';
import websiteNavbarData from 'website.navbar';
import Widget from 'web.Widget';
import { Markup } from 'web.utils';

import { registry } from "@web/core/registry";

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
        'click input#visibility_password': '_onPasswordClicked',
        'change input#visibility_password': '_onPasswordChanged',
        'change select#visibility': '_onVisibilityChanged',
        'error.datetimepicker': '_onDateTimePickerError',
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
            {text: _t("Discard"), classes: 'mr-auto', close: true},
        ];
        if (options.fromPageManagement) {
            buttons.push({
                text: _t("Go To Page"),
                icon: 'fa-globe',
                classes: 'btn-link',
                click: function (e) {
                    window.location.href = '/' + self.page.url;
                },
            });
        }
        buttons.push({
            text: _t("Duplicate Page"),
            icon: 'fa-clone',
            classes: 'btn-link',
            click: function (e) {
                // modal('hide') will break the rpc, so hide manually
                this.$el.closest('.modal').addClass('d-none');
                _clonePage.call(this, self.page_id);
            },
        });
        buttons.push({
            text: _t("Delete Page"),
            icon: 'fa-trash',
            classes: 'btn-link',
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
            method: 'get_page_properties',
            args: [this.page_id],
        }).then(function (page) {
            page.url = _.str.startsWith(page.url, '/') ? page.url.substring(1) : page.url;
            page.hasSingleGroup = page.group_id !== undefined;
            self.page = page;
        }));

        return Promise.all(defs);
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
        if (this.page.visibility !== 'password') {
            this.$('.show_visibility_password').addClass('d-none');
        }
        if (this.page.visibility !== 'restricted_group') {
            this.$('.show_group_id').addClass('d-none');
        }
        this.autocompleteWithGroups(this.$('#group_id'));

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
            self.$('a.o_dependencies_redirect_link').on('click', () => {
                self.$('.o_dependencies_redirect_list_popover').popover({
                    html: true,
                    title: _t('Dependencies'),
                    boundary: 'viewport',
                    placement: 'right',
                    trigger: 'focus',
                    content: () => {
                        return qweb.render('website.get_tooltip_dependencies', {
                            dependencies: dependencies,
                        });
                    },
                    template: qweb.render('website.page_dependencies_popover'),
                }).popover('toggle');
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
            minDate: moment({ y: 1000 }),
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
        return Promise.all(defs);
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
        var context;
        this.trigger_up('context_get', {
            callback: function (ctx) {
                context = ctx;
            },
        });
        var url = this.$('#page_url').val();

        var $datePublish = this.$("#date_publish");
        $datePublish.closest(".form-group").removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
        var datePublish = $datePublish.val();
        if (datePublish !== "") {
            datePublish = this._parse_date(datePublish);
            if (!datePublish) {
                $datePublish.closest(".form-group").addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
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
            visibility: this.$('#visibility').val(),
            date_publish: datePublish,
        };
        if (this.page.hasSingleGroup && this.$('#visibility').val() === 'restricted_group') {
            params['group_id'] = this.$('#group_id').data('group-id');
        }
        if (this.$('#visibility').val() === 'password') {
            var field_pwd = $('#visibility_password');
            if (!field_pwd.get(0).reportValidity()) {
                return;
            }
            if (field_pwd.data('dirty')) {
                params['visibility_pwd'] = field_pwd.val();
            }
        }

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
     * @returns {Promise<Array>}
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
     * @returns {Promise<Array>}
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
     * @returns {Promise<Array>}
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
    /**
     * Allows the given input to propose existing groups.
     *
     * @param {jQuery} $input
     */
    autocompleteWithGroups: function ($input) {
        $input.autocomplete({
            source: (request, response) => {
                return this._rpc({
                    model: 'res.groups',
                    method: 'search_read',
                    args: [[['name', 'ilike', request.term]], ['display_name']],
                    kwargs: {
                        limit: 15,
                    },
                }).then(founds => {
                    founds = founds.map(g => ({'id': g['id'], 'label': g['display_name']}));
                    response(founds);
                });
            },
            change: (ev, ui) => {
                var $target = $(ev.target);
                if (!ui.item) {
                    $target.val("");
                    $target.removeData('group-id');
                } else {
                    $target.data('group-id', ui.item.id);
                }
            },
        });
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
    /**
     * @private
     */
    _onVisibilityChanged: function (ev) {
        this.$('.show_visibility_password').toggleClass('d-none', ev.target.value !== 'password');
        this.$('.show_group_id').toggleClass('d-none', ev.target.value !== 'restricted_group');
        this.$('#visibility_password').attr('required', ev.target.value === 'password');
    },
    /**
     * Library clears the wrong date format so just ignore error
     *
     * @private
     */
    _onDateTimePickerError: function (ev) {
        return false;
    },
    /**
     * @private
     */
    _onPasswordClicked: function (ev) {
        ev.target.value = '';
        this._onPasswordChanged();
    },
    /**
     * @private
     */
    _onPasswordChanged: function () {
        this.$('#visibility_password').data('dirty', 1);
    },
});

var MenuEntryDialog = weWidgets.LinkDialog.extend({
    /**
     * @constructor
     */
    init: function (parent, options, editable, data) {
        this._super(parent, _.extend({
            title: _t("Add a menu item"),
        }, options || {}), editable, _.extend({
            needLabel: true,
            content: data.name || '',
            isNewWindow: data.new_window,
        }, data || {}));

        this.linkWidget.xmlDependencies = this.linkWidget.xmlDependencies.concat(['/website/static/src/xml/website.contentMenu.xml']);

        const oldSave = this.linkWidget.save;
        /**
         * @override
         */
        this.linkWidget.save = () => {
            var $e = this.$('#o_link_dialog_label_input');
            if (!$e.val() || !$e[0].checkValidity()) {
                $e.closest('.form-group').addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
                $e.focus();
                return Promise.reject();
            }
            return oldSave.bind(this.linkWidget)();
        };

        this.menuType = data.menuType;
    },
    /**
     * @override
     */
    start: async function () {
        const res = await this._super(...arguments);

        // Remove style related elements
        this.$('.o_link_dialog_preview').remove();
        this.$('input[name="is_new_window"], .link-style').closest('.form-group').remove();
        this.$modal.find('.modal-lg').removeClass('modal-lg');
        this.$('form.col-lg-8').removeClass('col-lg-8').addClass('col-12');

        // Adapt URL label
        this.$('label[for="o_link_dialog_label_input"]').text(_t("Menu Label"));

        // Auto add '#' URL and hide the input if for mega menu
        if (this.menuType === 'mega') {
            var $url = this.$('input[name="url"]');
            $url.val('#').trigger('change');
            $url.closest('.form-group').addClass('d-none');
        }

        return res;
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
            // Remove name fallback in master
            self.roots.push({id: $(this).data('content_menu_id'), name: $(this).attr('name') || $(this).data('menu_name')});
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
        var context;
        this.trigger_up('context_get', {
            callback: function (ctx) {
                context = ctx;
            },
        });
        defs.push(this._rpc({
            model: 'website.menu',
            method: 'get_tree',
            args: [context.website_id, this.rootID],
        }).then(menu => {
            this.menu = menu;
            this.rootMenuID = menu.fields['id'];
            this.flat = this._flatenize(menu);
            this.toDelete = [];
        }));
        return Promise.all(defs);
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
            isAllowed: (placeholder, placeholderParent, currentItem) => {
                return !placeholderParent
                    || !currentItem[0].dataset.megaMenu && !placeholderParent[0].dataset.megaMenu;
            },
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
        var newMenus = this.$('.oe_menu_editor').nestedSortable('toArray', {startDepthCount: 0});
        var levels = [];
        var data = [];
        var context;
        this.trigger_up('context_get', {
            callback: function (ctx) {
                context = ctx;
            },
        });
        // Resequence, re-tree and remove useless data
        newMenus.forEach(menu => {
            if (menu.id) {
                levels[menu.depth] = (levels[menu.depth] || 0) + 1;
                var menuFields = this.flat[menu.id].fields;
                menuFields['sequence'] = levels[menu.depth];
                menuFields['parent_id'] = menu['parent_id'] || this.rootMenuID;
                data.push(menuFields);
            }
        });
        return this._rpc({
            model: 'website.menu',
            method: 'save',
            args: [
                context.website_id,
                {
                    'data': data,
                    'to_delete': this.toDelete,
                }
            ],
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
        _dict[node.fields['id']] = node;
        node.children.forEach(child => {
            this._flatenize(child, _dict);
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
     * @param {Event} ev
     */
    _onAddMenuButtonClick: function (ev) {
        var menuType = ev.currentTarget.dataset.type;
        var dialog = new MenuEntryDialog(this, {}, null, {
            menuType: menuType,
        });
        dialog.on('save', this, link => {
            var newMenu = {
                'fields': {
                    'id': _.uniqueId('new-'),
                    'name': _.unescape(link.content),
                    'url': link.url,
                    'new_window': link.isNewWindow,
                    'is_mega_menu': menuType === 'mega',
                    'sequence': 0,
                    'parent_id': false,
                },
                'children': [],
                'is_homepage': false,
            };
            this.flat[newMenu.fields['id']] = newMenu;
            this.$('.oe_menu_editor').append(
                qweb.render('website.contentMenu.dialog.submenu', {submenu: newMenu})
            );
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
        var menuID = parseInt($menu.data('menu-id'));
        if (menuID) {
            this.toDelete.push(menuID);
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
        var $menu = $(ev.currentTarget).closest('[data-menu-id]');
        var menuID = $menu.data('menu-id');
        var menu = this.flat[menuID];
        if (menu) {
            var dialog = new MenuEntryDialog(this, {}, null, _.extend({
                menuType: menu.fields['is_mega_menu'] ? 'mega' : undefined,
            }, menu.fields));
            dialog.on('save', this, link => {
                _.extend(menu.fields, {
                    'name': _.unescape(link.content),
                    'url': link.url,
                    'new_window': link.isNewWindow,
                });
                $menu.find('.js_menu_label').first().text(menu.fields['name']);
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
        header_visible: function (value) {
            $('#wrapwrap > header').toggleClass('d-none o_snippet_invisible', !value);
        },
        footer_visible: function (value) {
            $('#wrapwrap > footer').toggleClass('d-none o_snippet_invisible', !value);
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
     * @returns {Promise}
     *          Unresolved if the menu is edited and saved as the page will be
     *          reloaded.
     *          Resolved otherwise.
     */
    _editMenu: function (beforeReloadCallback) {
        var self = this;
        return new Promise(function (resolve) {
            function resolveWhenEditMenuDialogIsCancelled(rootID) {
                return self._openEditMenuDialog(rootID, beforeReloadCallback).then(resolve);
            }
            if ($('[data-content_menu_id]').length) {
                var select = new SelectEditMenuDialog(self);
                select.on('save', self, resolveWhenEditMenuDialogIsCancelled);
                select.on('cancel', self, resolve);
                select.open();
            } else {
                resolveWhenEditMenuDialogIsCancelled(null);
            }
        });
    },
    /**
     *
     * @param {*} rootID
     * @param {function|undefied} beforeReloadCallback function that returns a promise
     * @returns {Promise}
     */
    _openEditMenuDialog: function (rootID, beforeReloadCallback) {
        var self = this;
        return new Promise(function (resolve) {
            var dialog = new EditMenuDialog(self, {}, rootID);
            dialog.on('save', self, function () {
                window.document.body.classList.add('o_wait_reload');
                // Before reloading the page after menu modification, does the
                // given action to do.
                if (beforeReloadCallback) {
                    // Reload the page so that the menu modification are shown
                    beforeReloadCallback().then(function () {
                        window.location.reload(true);
                    });
                } else {
                    window.location.reload(true);
                }
            });
            dialog.on('cancel', self, resolve);
            dialog.open();
        });
    },

    /**
     * Retrieves the value of a page option.
     *
     * @private
     * @param {string} name
     * @returns {Promise<*>}
     */
    _getPageOption: function (name) {
        var option = this.pageOptions[name];
        if (!option) {
            return Promise.reject();
        }
        return Promise.resolve(option.value);
    },
    /**
     * On save, simulated page options have to be server-saved.
     *
     * @private
     * @returns {Promise}
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
        return Promise.all(defs);
    },
    /**
     * Opens the page properties dialog.
     *
     * @private
     * @returns {Promise}
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
     * @returns {Promise}
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
            return Promise.reject();
        }

        // Check if this is a valid option
        var option = this.pageOptions[params.name];
        if (!option) {
            return Promise.reject();
        }

        // Toggle the value
        option.setValue(params.value);

        // If simulate is true, it means we want the option to be toggled but
        // not saved on the server yet
        if (!forceSave) {
            // Add the 'o_dirty' class on an editable element specific to the
            // page to notify the editor that the page should be saved,
            // otherwise it won't save anything if it doesn't detect any change
            // inside the #wrapwrap. (e.g. the header "over the content" option
            // which adds a class on the #wrapwrap itself and not inside it).
            const pageEl = document.querySelector(`.o_editable[data-oe-model="ir.ui.view"][data-oe-id="${mo.viewid}"]`);
            if (pageEl) {
                pageEl.classList.add('o_dirty');
            }
            return Promise.resolve();
        }

        // If not, write on the server page and reload the current location
        var vals = {};
        vals[params.name] = option.value;
        var prom = this._rpc({
            model: 'website.page',
            method: 'write',
            args: [[mo.id], vals],
        });
        if (noReload) {
            return prom;
        }
        return prom.then(function () {
            window.location.reload();
            return new Promise(function () {});
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
     * @returns {Promise<Array>}
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
        _clonePage.call(this, pageId);
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
async function _deletePage(pageId, fromPageManagement) {
    const dependencies = await this._getPageDependencies(pageId);
    for (const locs of Object.values(dependencies)) {
        for (const loc of locs) {
            loc.text = Markup(loc.text);
        }
    }
    Dialog.safeConfirm(this, "", {
        title: _t("Delete Page"),
        $content: $(qweb.render('website.delete_page', {dependencies: dependencies})),
        async confirm_callback() {
            await this._rpc({model: 'website.page', method: 'unlink', args: [pageId]});
            if (fromPageManagement) {
                window.location.reload(true);
            } else {
                window.location.href = '/';
            }
        }
    });
}
/**
 * Duplicate the page after showing the wizard to enter new page name.
 *
 * @private
 * @param {integer} pageId - The ID of the page to be duplicate
 *
 */
function _clonePage(pageId) {
    var self = this;
    new Promise(function (resolve, reject) {
        Dialog.confirm(this, undefined, {
            title: _t("Duplicate Page"),
            $content: $(qweb.render('website.duplicate_page_action_dialog')),
            confirm_callback: function () {
                var new_page_name =  this.$('#page_name').val();
                return self._rpc({
                    model: 'website.page',
                    method: 'clone_page',
                    args: [pageId, new_page_name],
                }).then(function (path) {
                    window.location.href = path;
                }).guardedCatch(reject);
            },
            cancel_callback: reject,
        }).on('closed', null, reject);
    });
}

registry.category("website_navbar_widgets").add("ContentMenu", {
    Widget: ContentMenu,
    selector: '#content-menu',
});
registry.category("public_root_widgets").add("PageManagement", {
    Widget: PageManagement,
    selector: '#list_website_pages',
});

export default {
    PagePropertiesDialog: PagePropertiesDialog,
    ContentMenu: ContentMenu,
    EditMenuDialog: EditMenuDialog,
    MenuEntryDialog: MenuEntryDialog,
    SelectEditMenuDialog: SelectEditMenuDialog,
};
