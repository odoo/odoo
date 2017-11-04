odoo.define('website.customizeMenu', function (require) {
'use strict';

var core = require('web.core');
var Widget = require('web.Widget');
var weContext = require('web_editor.context');
var websiteNavbarData = require('website.navbar');
var WebsiteAceEditor = require('website.ace');

var qweb = core.qweb;

var CustomizeMenu = Widget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],
    events: {
        'click > ul a[data-view-id]': '_onCustomizeOptionClick',
    },

    /**
     * @override
     */
    start: function () {
        var viewName = $(document.documentElement).data('view-xmlid');
        if (!viewName) {
            _.defer(this.destroy.bind(this));
        }

        if (this.$el.is('.open')) {
            this._loadCustomizeOptions(viewName);
        } else {
            this.$el.one('mousedown', '> a.dropdown-toggle', this._loadCustomizeOptions.bind(this, viewName));
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Enables/Disables a view customization whose id is given.
     *
     * @private
     * @param {integer} viewID
     * @returns {Deferred}
     *          Unresolved if the customization succeeded as the page will be
     *          reloaded.
     *          Rejected otherwise.
     */
    _doCustomize: function (viewID) {
        return this._rpc({
            model: 'ir.ui.view',
            method: 'toggle',
            args: [[viewID]],
            context: weContext.get(),
        }).then(function () {
            window.location.reload();
            return $.Deferred();
        });
    },
    /**
     * Loads the information about the views which can be enabled/disabled on
     * the current page and shows them as switchable elements in the menu.
     *
     * @private
     * @param {string} viewName - xml id
     * @return {Deferred}
     */
    _loadCustomizeOptions: function (viewName) {
        var $menu = this.$el.children('ul');
        return this._rpc({
            route: '/website/get_switchable_related_views',
            params: {
                key: viewName,
            },
        }).then(function (result) {
            var currentGroup = '';
            _.each(result, function (item) {
                if (currentGroup !== item.inherit_id[1]) {
                    currentGroup = item.inherit_id[1];
                    $menu.append('<li class="dropdown-header">' + currentGroup + '</li>');
                }
                var $li = $('<li/>', {role: 'presentation'})
                            .append($('<a/>', {href: '#', 'data-view-id': item.id, role: 'menuitem'})
                                .append(qweb.render('web_editor.components.switch', {id: 'switch-' + item.id, label: item.name})));
                $li.find('input').prop('checked', !!item.active);
                $menu.append($li);
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
    _onCustomizeOptionClick: function (ev) {
        ev.preventDefault();
        var viewID = parseInt($(ev.currentTarget).data('view-id'), 10);
        this._doCustomize(viewID);
    },
});

var AceEditorMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions || {}, {
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
        var def;
        if (window.location.hash.substr(0, WebsiteAceEditor.prototype.hash.length) === WebsiteAceEditor.prototype.hash) {
            def = this._launchAce();
        }
        return $.when(this._super.apply(this, arguments), def);
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
        if (this.globalEditor) {
            this.globalEditor.do_hide();
        }
    },
    /**
     * Launches the ace editor to be able to edit the templates and less files
     * which are used by the current page.
     *
     * @private
     * @returns {Deferred}
     */
    _launchAce: function () {
        if (this.globalEditor) {
            this.globalEditor.do_show();
            return $.when();
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

            this.globalEditor = new WebsiteAceEditor(this, $(document.documentElement).data('view-xmlid'), {
                initialResID: initialResID,
                defaultBundlesRestriction: [
                    "web.assets_frontend",
                    "website.assets_frontend",
                ],
            });
            return this.globalEditor.appendTo(document.body);
        }
    },
});

websiteNavbarData.websiteNavbarRegistry.add(CustomizeMenu, '#customize-menu');
websiteNavbarData.websiteNavbarRegistry.add(AceEditorMenu, '#html_editor');

return CustomizeMenu;
});
