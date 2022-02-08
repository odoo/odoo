odoo.define('website.customizeMenu', function (require) {
'use strict';

var core = require('web.core');
var Widget = require('web.Widget');
var websiteNavbarData = require('website.navbar');
var WebsiteAceEditor = require('website.ace');

const { registry } = require("@web/core/registry");

var qweb = core.qweb;

var CustomizeMenu = Widget.extend({
    xmlDependencies: ['/website/static/src/xml/website.editor.xml'],
    events: {
        'show.bs.dropdown': '_onDropdownShow',
        'change .dropdown-item[data-view-key]': '_onCustomizeOptionChange',
    },

    /**
     * @override
     */
    willStart: function () {
        this.viewName = $(document.documentElement).data('view-xmlid');
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    start: function () {
        if (!this.viewName) {
            _.defer(this.destroy.bind(this));
        }

        if (this.$el.is('.show')) {
            this._loadCustomizeOptions();
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Enables/Disables a view customization whose id is given.
     *
     * @private
     * @param {string} viewKey
     * @returns {Promise}
     *          Unresolved if the customization succeeded as the page will be
     *          reloaded.
     *          Rejected otherwise.
     */
    _doCustomize: function (viewKey) {
        return this._rpc({
            route: '/website/toggle_switchable_view',
            params: {
                'view_key': viewKey,
            },
        }).then(function () {
            window.location.reload();
            return new Promise(function () {});
        });
    },
    /**
     * Loads the information about the views which can be enabled/disabled on
     * the current page and shows them as switchable elements in the menu.
     *
     * @private
     * @return {Promise}
     */
    _loadCustomizeOptions: function () {
        if (this.__customizeOptionsLoaded) {
            return Promise.resolve();
        }
        this.__customizeOptionsLoaded = true;

        var $menu = this.$el.children('.dropdown-menu');
        return this._rpc({
            route: '/website/get_switchable_related_views',
            params: {
                key: this.viewName,
            },
        }).then(function (result) {
            var currentGroup = '';
            if (result.length) {
                $menu.append($('<div/>', {
                    class: 'dropdown-divider',
                    role: 'separator',
                }));
            }
            _.each(result, function (item) {
                if (currentGroup !== item.inherit_id[1]) {
                    currentGroup = item.inherit_id[1];
                    $menu.append('<li class="dropdown-header">' + currentGroup + '</li>');
                }
                var $label = $(qweb.render('website.components.switch', {id: 'switch-' + item.id, label: item.name}));
                $label.attr("data-view-key", item.key);
                $label.find('input').prop('checked', !!item.active);
                $menu.append($label);
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a view's related switchable element is clicked -> enable /
     * disable the related view.
     *
     * @private
     * @param {Event} ev
     */
    _onCustomizeOptionChange: function (ev) {
        ev.preventDefault();
        var viewKey = $(ev.currentTarget).data('viewKey');
        this._doCustomize(viewKey);
    },
    /**
     * @private
     */
    _onDropdownShow: function () {
        this._loadCustomizeOptions();
    },
});

var AceEditorMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions || {}, {
        close_all_widgets: '_hideEditor',
        edit: '_enterEditMode',
        ace: '_launchAce',
    }),

    /**
     * Launches the ace editor automatically when the corresponding hash is in
     * the page URL.
     *
     * @override
     */
    start: function () {
        if (window.location.hash.substr(0, WebsiteAceEditor.prototype.hash.length) === WebsiteAceEditor.prototype.hash) {
            this._launchAce();
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * When handling the "edit" website action, the ace editor has to be closed.
     *
     * @private
     */
    _enterEditMode: function () {
        this._hideEditor();
    },
    /**
     * @private
     */
    _hideEditor: function () {
        if (this.globalEditor) {
            this.globalEditor.do_hide();
        }
    },
    /**
     * Launches the ace editor to be able to edit the templates and scss files
     * which are used by the current page.
     *
     * @private
     * @returns {Promise}
     */
    _launchAce: function () {
        var self = this;
        var prom = new Promise(function (resolve, reject) {
            self.trigger_up('action_demand', {
                actionName: 'close_all_widgets',
                onSuccess: resolve,
            });
        });
        prom.then(function () {
            if (self.globalEditor) {
                self.globalEditor.do_show();
                return Promise.resolve();
            } else {
                var currentHash = window.location.hash;
                var indexOfView = currentHash.indexOf("?res=");
                var initialResID = undefined;
                if (indexOfView >= 0) {
                    initialResID = currentHash.substr(indexOfView + ("?res=".length));
                    var parsedResID = parseInt(initialResID, 10);
                    if (parsedResID) {
                        initialResID = parsedResID;
                    }
                }

                self.globalEditor = new WebsiteAceEditor(self, $(document.documentElement).data('view-xmlid'), {
                    initialResID: initialResID,
                    defaultBundlesRestriction: [
                        'web.assets_frontend',
                        'web.assets_frontend_minimal',
                        'web.assets_frontend_lazy',
                    ],
                });
                return self.globalEditor.appendTo(document.body);
            }
        });

        return prom;
    },
});

registry.category("website_navbar_widgets").add("CustomizeMenu", {
    Widget: CustomizeMenu,
    selector: '#customize-menu',
});
registry.category("website_navbar_widgets").add("AceEditorMenu", {
    Widget: AceEditorMenu,
    selector: '#html_editor',
});

return CustomizeMenu;
});
