/** @odoo-module **/

import ChatbotFormController from '@im_livechat/js/im_livechat_chatbot_form_controller';

import FormRenderer from 'web.FormRenderer';
import FormView from 'web.FormView';
import viewRegistry from 'web.view_registry';

/**
 * FormView override for the chatbot.script model.
 * This override will properly handle chatbot.script.step sequences while building your
 * chatbot.script, which is critically important since steps order will define how the script runs.
 *
 * To be used on the main chatbot.script model form view, along with its "script_step_ids" field,
 * and not elsewhere as it would not be compatible.
 */
const ChatbotFormView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Controller: ChatbotFormController,
        Renderer: FormRenderer,
    }),
});

viewRegistry.add('im_livechat_chatbot_form_view', ChatbotFormView);

export default ChatbotFormView;
