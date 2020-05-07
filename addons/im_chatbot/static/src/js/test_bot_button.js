odoo.define("im_chatbot.test_button", function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require("web.Widget");
    const registry = require("web.widget_registry");
    var qweb = core.qweb;

    var extended = Widget.extend({
        template: "im_chatbot.test_button",
        xmlDependencies: ["/im_chatbot/static/src/xml/template.xml"],
        events: {
            "click .test_chatbot": "_fire_chat_bot"
        },
        init: function (parent, value) {
            this._super(parent);
        },
        start() {
            //
        },
        _fire_chat_bot() {
            var chatbot_id = $(".chatbot_id span").html();
            console.log("test");
            this._rpc({
                model: 'im_chatbot.chatbot',
                method: 'test_bot',
                // args: [
                //     chatbot_id
                // ],
            }).then(function (response) {
                //
            });
        }
    });

    registry.add("im_chatbot.test_button", extended);

    return extended;
});
