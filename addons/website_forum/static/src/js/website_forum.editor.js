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
    events: _.extend({}, Dialog.prototype.events, {
        'change input[name="privacy"]': '_onPrivacyChanged',
    }),

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
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var $input = self.$('#group_id');
            $input.select2({
                width: '100%',
                allowClear: true,
                formatNoMatches: false,
                multiple: false,
                selection_data: false,
                fill_data: function (query, data) {
                    var that = this;
                    var tags = {results: []};
                    _.each(data, function (obj) {
                        if (that.matcher(query.term, obj.display_name)) {
                            tags.results.push({id: obj.id, text: obj.display_name});
                        }
                    });
                    query.callback(tags);
                },
                query: function (query) {
                    var that = this;
                    // fetch data only once and store it
                    if (!this.selection_data) {
                        self._rpc({
                            model: 'res.groups',
                            method: 'search_read',
                            args: [[], ['display_name']],
                        }).then(function (data) {
                            that.fill_data(query, data);
                            that.selection_data = data;
                        });
                    } else {
                        this.fill_data(query, this.selection_data);
                    }
                }
            });
        });
    },
    onCreateClick: function () {
        var $dialog = this.$el;
        var $forumName = $dialog.find('input[name=forum_name]');
        if (!$forumName.val()) {
            $forumName.addClass('border-danger');
            return;
        }
        var $forumPrivacyGroup = $dialog.find('input[name=group_id]');
        var forumPrivacy = $dialog.find('input:radio[name=privacy]:checked').val();
        if (forumPrivacy === 'private' && !$forumPrivacyGroup.val()) {
            this.$("#group-required").removeClass('d-none');
            return;
        }
        var addMenu = ($dialog.find('input[type="checkbox"]').is(':checked'));
        var forumMode = $dialog.find('input:radio[name=mode]:checked').val();
        return this._rpc({
            route: '/forum/new',
            params: {
                forum_name: $forumName.val(),
                forum_mode: forumMode,
                forum_privacy: forumPrivacy,
                forum_privacy_group: $forumPrivacyGroup.val(),
                add_menu: addMenu || "",
            },
        }).then(function (url) {
            window.location.href = url;
            return new Promise(function () {});
        });
    },
    /**
     * @private
     */
    _onPrivacyChanged: function (ev) {
        this.$('.show_visibility_group').toggleClass('d-none', ev.target.value !== 'private');
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
