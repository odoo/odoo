odoo.define("im_chatbot.WebsiteLivechatMessage", function (require) {
"use strict";

    var WebsiteLivechatMessage = require('im_livechat.model.WebsiteLivechatMessage');

    WebsiteLivechatMessage.include({
        events: _.extend({}, WebsiteLivechatMessage.prototype.events, {
            "click .chatbot_badge": "_onclick_badge",
        }),
        init: function() {
            console.log("Init");
            this._super.apply(this, arguments);
        },
        start: function() {
            console.log("start");
            console.log(this.$el);
            this._super.apply(this, arguments);
        },
        _onclick_badge: function(event) {
            console.log("badge_click");
        }
    });

    return WebsiteLivechatMessage;
});
