/** @odoo-module **/

import { _t } from 'web.core';
import FormController from 'web.FormController';
import ChatbotStepFormViewDialog from 'im_livechat.ChatbotStepFormViewDialog';

const ChatbotFormController = FormController.extend({
    custom_events: Object.assign({}, FormController.prototype.custom_events, {
        chatbot_save_form: '_chatbotSaveForm',
        chatbot_add_step: '_chatbotAddStep',
    }),

    /**
     * Force the form save when a step is added.
     *
     * This is done in order to allow selecting previous step's answers for the
     * 'triggering_answer_ids' fields.
     *
     * @param {OdooEvent} ev
     */
    async _chatbotSaveForm(ev) {
        await this.saveRecord(this.handle, {
            stayInEdit: true,
        });

        if (ev && ev.data.callback) {
            ev.data.callback();
        }

        const state = this.model.get(this.handle);
        this.renderer.confirmChange(state, state.id, ['script_step_ids']);
    },

    /**
     * Steps are added using the 'script_step_ids' list view button to ensure that the sequence is
     * correctly incremented each time we add a step.
     *
     * This handler will trigger the click event on the "Add a line" button of the embedded list view.
     *
     * @param {OdooEvent} ev
     */
    async _chatbotAddStep(ev) {
        this.$('.o_field_one2many[name="script_step_ids"] .o_field_x2many_list_row_add a').click();
        if (ev && ev.data.callback) {
            ev.data.callback();
        }
    },

    /**
     * Adapt the FormView to call our custom Dialog for chatbot steps.
     * See 'ChatbotStepFormViewDialog' for more info.
     *
     * The rest is copy/pasted from the initial method.
     *
     * @param {OdooEvent} ev
     */
    async _onOpenOne2ManyRecord(ev) {
        ev.stopPropagation();
        const data = ev.data;

        if (data.field.relation !== "chatbot.script.step") {
            return this._super(...arguments);
        }

        const record = data.id ? this.model.get(data.id, {raw: true}) : null;

        // Sync with the mutex to wait for potential onchanges
        await this.model.mutex.getUnlockedDef();

        new ChatbotStepFormViewDialog(this, {
            context: data.context,
            domain: data.domain,
            fields_view: data.fields_view,
            model: this.model,
            on_saved: data.on_saved,
            on_remove: data.on_remove,
            parentID: data.parentID,
            readonly: data.readonly,
            editable: data.editable,
            deletable: record ? data.deletable : false,
            disable_multiple_selection: true,
            recordID: record && record.id,
            res_id: record && record.res_id,
            res_model: data.field.relation,
            shouldSaveLocally: true,
            title: (record ? _t("Open: ") : _t("Create ")) + (ev.target.string || data.field.string),
        }).open();
    },

});

export default ChatbotFormController;
