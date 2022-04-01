/** @odoo-module **/

import { FieldMany2ManyTags } from 'web.relational_fields';
import FieldRegistry from 'web.field_registry';

const ChatbotScriptTriggeringAnswersMany2Many = FieldMany2ManyTags.extend({

    /**
     * Small rendering override that adds additional context into the linked many2one element.
     * This allows limiting the displayed result to the chatbot we are currently configuring.
     * See chatbot.script.answer#_name_search() for more details.
     *
     * @override
     * @private
     */
    _renderEdit: function () {
        const renderResult = this._super(...arguments);

        if (this.many2one) {
            this.many2one.additionalContext.force_domain_chatbot_script_id = this._getChatbotId();
        }
        return renderResult;
    },

    /**
     * Return the related chatbot.script ID record that we are currently configuring.
     *
     * @private
     */
    _getChatbotId: function () {
        const chatbotForm = this._findChatbotForm();
        return chatbotForm
            ? chatbotForm.model.localData[chatbotForm.handle].res_id
            : false;
    },

    /**
     * Loop through parents to find our chatbot.script parent form.
     * (Not very elegant but not sure how we could do otherwise).
     *
     * @private
     */
    _findChatbotForm: function (previousParent) {
        const parent = previousParent ? previousParent.getParent() : this.getParent();
        if (parent.modelName === "chatbot.script") {
            return parent;
        } else {
            return this._findChatbotForm(parent);
        }
    }

});

FieldRegistry.add('chatbot_triggering_answers_widget', ChatbotScriptTriggeringAnswersMany2Many);
