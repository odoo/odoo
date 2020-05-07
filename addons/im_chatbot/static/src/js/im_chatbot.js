odoo.define('im_chatbot.chatBot', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var FormRenderer = require('web.FormRenderer');
    var viewRegistry = require('web.view_registry');

    var test_button = require("im_chatbot.test_button");

    var chatbotFormRenderer = FormRenderer.extend({
        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                console.log("test");
            });
        }
    });

    var chatbotChat = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: FormController,
            Renderer: chatbotFormRenderer
        }),
    });

    viewRegistry.add('im_chatbot.chatBot', chatbotChat);

    return chatbotChat;
});
