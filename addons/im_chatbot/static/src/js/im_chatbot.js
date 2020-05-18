odoo.define('im_chatbot.chatBot', function (require) {
    "use strict";

    var LivechatButton = require('im_livechat.im_livechat').LivechatButton;

    LivechatButton.include({
        events: _.extend({}, LivechatButton.prototype.events, {
            "click .chatbot_badge": "_onclick_badge"
        }),
        _addMessage: function (data, options) {
            // Sometime, for unknown reason, this._livechat is null
            if (this._livechat) {
                // Start the is typing animation ?
                this._livechat.registerTyping({ partnerID: this._livechat._operatorPID[0] });

                // If the messages came from the visitor, we can "ping" the bot to
                // answer
                if (data.author_id[0] != this._livechat._operatorPID[0]) {
                    // Set timeout then send the "bot react by rpc"
                    setTimeout(() => {
                        this._rpc({
                            "route": "/im_chatbot/answer",
                            params: {
                                operator: this._livechat._operatorPID,
                                channel_id: this._livechat._id
                            }
                        }).then((response) => {

                            // Remove typing animation
                            this._livechat.unregisterTyping({ partnerID: this._livechat._operatorPID[0] });
                        });
                    }, 2000);
                }
            }

            this._super.apply(this, arguments);
        },
    });

    return {
        LivechatButton: LivechatButton,
    };
});
