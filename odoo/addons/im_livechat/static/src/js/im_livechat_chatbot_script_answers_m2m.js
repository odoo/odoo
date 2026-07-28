/* @odoo-module */

import { registry } from "@web/core/registry";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";

const fieldRegistry = registry.category("fields");

export class ChatbotScriptTriggeringAnswersMany2Many extends Many2ManyTagsField {
    /**
     * Force the chatbot script ID we are currently editing into the context.
     * This allows to filter triggering question answers on steps of this script.
     */
    setup() {
        super.setup();

        if (this.props.record.model.root.resId) {
            this.env.services.user.updateContext({
                force_domain_chatbot_script_id: this.props.record.model.root.resId,
            });
        }
    }
}

export const chatbotScriptTriggeringAnswersMany2Many = {
    ...many2ManyTagsField,
    component: ChatbotScriptTriggeringAnswersMany2Many,
};

fieldRegistry.add("chatbot_triggering_answers_widget", chatbotScriptTriggeringAnswersMany2Many);
