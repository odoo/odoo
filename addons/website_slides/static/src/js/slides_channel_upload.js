odoo.define('website_slides.upload_channel', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');

var _t = core._t;


var ChannelCreateDialog = Dialog.extend({
    template: 'website.slide.channel.create',

    /**
     * @override
     */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            title: _t("New Channel Slide"),
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
        this.channelData = _.defaults(options.channelData || {}, {
            channelId: 1,
        });
    },

    /**
     *
     * @override
     */
    willStart: function () {
        var fetchDone = this._fetchChannelData();
        return $.when(
            this._super.apply(this, arguments),
            fetchDone
        );
    },

    /**
     *
     * @override
     */
    start: function () {
        var self = this;
        var defSuper = this._super.apply(this, arguments);
        return $.when(defSuper).then(function () {
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

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _fetchChannelData: function () {
        var self = this;
        var fetchDone = new $.Deferred();
        console.log('checking fetch channel data for ', this.channelData.channelId);
        if (this.channelData.channelId) {
            fetchDone = self._rpc({
                route: '/slides/channel/read',
                params: {
                    channel_id: self.channelData.channelId,
                }
            }).then(function (data) {
                console.log('received', data);
                if (data && ! data.error) {
                    console.log('success');
                    self.channelData = _.extend(self.channelData, data);
                    console.log(self.channelData);
                }
            });
        } else {
            fetchDone.resolve();
        }
        return fetchDone;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     *
     * @private
     * @param {event} event
     */
    _onClickFormSubmit: function (event) {
        var $form = this.$('#slide_channel_add_form');
        $form.submit();
    },
});


return {
    ChannelCreateDialog: ChannelCreateDialog,
};

});