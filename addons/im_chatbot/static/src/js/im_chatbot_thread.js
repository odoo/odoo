odoo.define("im_chatbot.widget.Thread", function (require) {
    "use strict";

    var ThreadWidget = require('mail.widget.Thread');

    ThreadWidget.include({
        events: _.extend({}, ThreadWidget.prototype.events, {
            "click .chatbot_badge": "_onclick_badge"
        }),
        _onclick_badge(event) {
            // here we need the action to perform to send to /im_chatbot/action
            var action = this.$(event.target).data("action");
            this._rpc({
                route: "/im_chatbot/action",
                params: {
                    action: action,
                    channel_id: this._currentThreadID
                }
            }).then((response) => {
                console.log(response);
            });
        }
    });

    return ThreadWidget;
});
