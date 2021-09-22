/** @odoo-module **/

import ImLivechatChannelFormController from '@im_livechat/js/im_livechat_channel_form_controller';

import FormView from 'web.FormView';
import viewRegistry from 'web.view_registry';

const ImLivechatChannelFormView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Controller: ImLivechatChannelFormController,
    }),
});

viewRegistry.add('im_livechat_channel_form_view_js', ImLivechatChannelFormView);

export default ImLivechatChannelFormView;
