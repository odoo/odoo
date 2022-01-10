/** @odoo-module **/

import ChatbotFormController from '@im_livechat/js/im_livechat_chatbot_form_controller';

import FormRenderer from 'web.FormRenderer';
import FormView from 'web.FormView';
import viewRegistry from 'web.view_registry';

const ChatbotFormView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Controller: ChatbotFormController,
        Renderer: FormRenderer,
    }),
});

viewRegistry.add('im_livechat_chatbot_form_view', ChatbotFormView);

export default ChatbotFormView;
