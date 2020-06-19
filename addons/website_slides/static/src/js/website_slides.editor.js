odoo.define('website_slides.editor', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var QWeb = core.qweb;
var WebsiteNewMenu = require('website.newMenu');
var wUtils = require('website.utils');

var _t = core._t;


var ChannelCreateDialog = Dialog.extend({
    template: 'website.slide.channel.create',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/website_slides/static/src/xml/website_slides_channel.xml']
    ),
    /**
     * @override
     * @param {Object} parent
     * @param {Object} options
     */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            title: _t("New Course"),
            size: 'medium',
            buttons: [{
                text: _t("Create"),
                classes: 'btn-primary',
                click: this._onClickFormSubmit.bind(this)
            }, {
                text: _t("Discard"),
                close: true
            },]
        });
        this._super(parent, options);
    },
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var $input = self.$('#tag_ids');
            $input.select2({
                width: '100%',
                allowClear: true,
                formatNoMatches: false,
                multiple: true,
                selection_data: false,
                fill_data: function (query, data) {
                    var that = this,
                        tags = {results: []};
                    _.each(data, function (obj) {
                        if (that.matcher(query.term, obj.name)) {
                            tags.results.push({id: obj.id, text: obj.name});
                        }
                    });
                    query.callback(tags);
                },
                query: function (query) {
                    var that = this;
                    // fetch data only once and store it
                    if (!this.selection_data) {
                        self._rpc({
                            route: '/slides/channel/tag/search_read',
                            params: {
                                fields: ['name'],
                                domain: [],
                            }
                        }).then(function (data) {
                            that.can_create = data.can_create;
                                that.fill_data(query, data.read_results);
                                that.selection_data = data.read_results;
                        });
                    } else {
                        this.fill_data(query, this.selection_data);
                    }
                }
            });
        });
    },
    _onClickFormSubmit: function (ev) {
        var $form = this.$("#slide_channel_add_form");
        var $title = this.$("#title");
        if (!$title[0].value){
            $title.addClass('border-danger');
            this.$("#title-required").removeClass('d-none');
        } else {
            $form.submit();
        }
    },
});

WebsiteNewMenu.include({
    actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
        new_slide_channel: '_createNewSlideChannel',
    }),

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Displays the popup to create a new slide channel,
     * and redirects the user to this channel.
     *
     * @private
     * @returns {Promise} Unresolved if there is a redirection
     */
     _createNewSlideChannel: function () {
        var self = this;
        var def = new Promise(function (resolve) {
            var dialog = new ChannelCreateDialog(self, {});
            dialog.open();
            dialog.on('closed', self, resolve);
        });
        return def;
     },
});
});
