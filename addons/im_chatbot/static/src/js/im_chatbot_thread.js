odoo.define("im_chatbot.widget.Thread", function (require) {
    "use strict";

    var ThreadWidget = require('mail.widget.Thread');

    ThreadWidget.include({
        events: _.extend({}, ThreadWidget.prototype.events, {
            "click .chatbot_badge": "_onclick_badge"
        }),
        _onclick_badge(event) {
            console.log("click badge");
        }
    });

    return ThreadWidget;
});
