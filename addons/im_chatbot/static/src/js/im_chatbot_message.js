odoo.define('im_chatbot.message', function (require) {
    "use strict";
    var WebsiteLivechatMessage = require('im_livechat.model.WebsiteLivechatMessage');

    WebsiteLivechatMessage.include({
        init() {
            console.log(this);
            return this._super.apply(this, arguments);
        }
    });

    return WebsiteLivechatMessage;
});
