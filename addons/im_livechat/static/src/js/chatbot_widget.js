/** @odoo-module **/

import { FieldOne2Many, FieldMany2ManyTags } from 'web.relational_fields';
import FieldRegistry from 'web.field_registry';

const ChatbotScriptStepOne2Many = FieldOne2Many.extend({

    _onAddRecord(ev) {
        const self = this;
        const fnSuper = this._super;
        const fnArguments = arguments;
        ev.data = { 'disable_multiple_selection': false };

        this.trigger_up('save_form_before_new_step', {
            callback: function () { fnSuper.apply(self, fnArguments); }
        });
    },

});

FieldRegistry.add('chatbot_script_step_widget', ChatbotScriptStepOne2Many);

const ChatbotScriptTriggeringAnswers = FieldMany2ManyTags.extend({

    _renderEdit: function () {
        this._super(...arguments);

        if (this.many2one) {
            this.many2one.additionalContext.force_domain_chatbot_id = this._getChatbotId();
        }
    },

    _getChatbotId: function () {
        let chatbotForm = this._findChatbotForm();
        if (chatbotForm) {
            return chatbotForm.model.localData[chatbotForm.handle].res_id;
        } else {
            return false;
        }
    },

    _findChatbotForm: function (previousParent) {
        let parent = previousParent ? previousParent.getParent() : this.getParent();
        if (parent.modelName === "im_livechat.chatbot.script") {
            return parent;
        } else {
            return this._findChatbotForm(parent);
        }
    }

});

FieldRegistry.add('chatbot_triggering_answers_widget', ChatbotScriptTriggeringAnswers);
