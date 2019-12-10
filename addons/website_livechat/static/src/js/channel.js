odoo.define('website.livechat.mail.model.Channel', function (require) {
"use strict";

var Channel = require('mail.model.Channel');
var session = require('web.session');

/**
 * This class represent channels in JS. In this context, the word channel
 * has the same meaning of channel on the server, meaning that direct messages
 * (DM) and livechats are also channels.
 *
 * Any piece of code in JS that make use of channels must ideally interact with
 * such objects, instead of direct data from the server.
 */
Channel.include({
    /**
     * @override
     * Add the visitor if is set on the channel
     * @param {Object} params
     * @param {Object} params.data
     * @param {string} params.data.visitor
     */
    init: function (params) {
        var self = this;
        var data = params.data;
        this._visitor = data.visitor;
        this._super.apply(this, arguments);
    },

});

return Channel;

});
