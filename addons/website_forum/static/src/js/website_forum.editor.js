odoo.define('website_forum.editor', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var SummernoteManager = require('web_editor.rte.summernote');
var WebsiteNewMenu = require('website.newMenu');
var wUtils = require('website.utils');
var websiteRootData = require('website.WebsiteRoot');

var _t = core._t;

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
     * @returns {Deferred} Unresolved if there is a redirection
     */
    _createNewForum: function () {
        var self = this;
        return wUtils.prompt({
            id: "editor_new_forum",
            window_title: _t("New Forum"),
            input: _t("Forum Name"),
            init: function () {
                var $group = this.$dialog.find("div.form-group");
                $group.removeClass("mb0");

                var $add = $(
                    '<div class="form-group mb0">'+
                        '<label class="offset-md-3 col-md-9 text-left">'+
                        '    <input type="checkbox" required="required"/> '+
                        '</label>'+
                    '</div>');
                $add.find('label').append(_t("Add to menu"));
                $group.after($add);
            }
        }).then(function (forum_name, field, $dialog) {
            if (!forum_name) {
                return;
            }
            var add_menu = ($dialog.find('input[type="checkbox"]').is(':checked'));
            return self._rpc({
                route: '/forum/new',
                params: {
                    forum_name: forum_name,
                    add_menu: add_menu || "",
                },
            }).then(function (url) {
                window.location.href = url;
                return $.Deferred();
            });
        });
    },
});

var WebsiteForumManager = Widget.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        new SummernoteManager(this);
    },
});
websiteRootData.websiteRootRegistry.add(WebsiteForumManager, '#wrapwrap');
});
