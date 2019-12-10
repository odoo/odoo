odoo.define('im_livechat.ImLivechatChannelFormView', function (require) {
"use strict";

const ImLivechatChannelFormController = require('im_livechat.ImLivechatChannelFormController');

const FormView = require('web.FormView');
const viewRegistry = require('web.view_registry');

const ImLivechatChannelFormView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Controller: ImLivechatChannelFormController,
    }),
});

viewRegistry.add('im_livechat_channel_form_view_js', ImLivechatChannelFormView);

return ImLivechatChannelFormView;

});
