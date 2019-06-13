odoo.define('website_forum.editor', function (require) {
"use strict";

var core = require('web.core');
var WebsiteNewMenu = require('website.newMenu');
var Dialog = require('web.Dialog');

var _t = core._t;

var ForumCreateDialog = Dialog.extend({
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/website_forum/static/src/xml/website_forum_templates.xml']
    ),
    template: 'website_forum.add_new_forum',

    /**
     * @override
     * @param {Object} parent
     * @param {Object} options
     */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            title: _t("New Forum"),
            size: 'medium',
            buttons: [
                {
                    text: _t("Create"),
                    classes: 'btn-primary',
                    click: this.onCreateClick.bind(this),
                },
                {
                    text: _t("Discard"),
                    close: true
                },
            ]
        });
        this._super(parent, options);
    },
    onCreateClick: function () {
        var $dialog = this.$el;
        var forumName = $dialog.find('input[name=forum_name]').val();;
        if (!forumName) {
            return;
        }
        var addMenu = ($dialog.find('input[type="checkbox"]').is(':checked'));
        var forumMode = $dialog.find('input[type="radio"]:checked').val();
        return this._rpc({
            route: '/forum/new',
            params: {
                forum_name: forumName,
                forum_mode: forumMode,
                add_menu: addMenu || "",
            },
        }).then(function (url) {
            window.location.href = url;
            return new Promise(function () {});
        });
    },
});

WebsiteNewMenu.include({
    actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
        new_forum: '_createNewForum',
    }),

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Asks the user information about a new forum to create, then creates it
     * and redirects the user to this new forum.
     *
     * @private
     * @returns {Promise} Unresolved if there is a redirection
     */
    _createNewForum: function () {
        var self = this;
        var def = new Promise(function (resolve) {
            var dialog = new ForumCreateDialog(self, {});
            dialog.open();
            dialog.on('closed', self, resolve);
        });
        return def;
    },
});
});
