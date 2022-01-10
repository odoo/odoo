/** @odoo-module **/

import { _t } from 'web.core';
import FormController from 'web.FormController';
import FormViewDialog from 'web.view_dialogs';

const ChatbotFormController = FormController.extend({
    custom_events: Object.assign({}, FormController.prototype.custom_events, {
        save_form_before_new_step: '_saveFormBeforeNewStep',
    }),

    async _saveFormBeforeNewStep(ev) {
        await this.saveRecord(null, {
            stayInEdit: true,
        });

        if (ev && ev.data.callback) {
            ev.data.callback();
        }
    },

    async _onOpenOne2ManyRecord(ev) {
        ev.stopPropagation();
        let data = ev.data;
        let record;
        if (data.id) {
            record = this.model.get(data.id, {raw: true});
        }

        // Sync with the mutex to wait for potential onchanges
        await this.model.mutex.getUnlockedDef();

        let previousOnSaved = data.on_saved;

        this._saveFormBeforeNewStep();
        new FormViewDialog.FormViewDialog(this, {
            context: data.context,
            domain: data.domain,
            fields_view: data.fields_view,
            model: this.model,
            on_saved: (record) => {
                previousOnSaved(record);
                this._saveFormBeforeNewStep();
            },
            on_remove: data.on_remove,
            parentID: data.parentID,
            readonly: data.readonly,
            editable: data.editable,
            deletable: record ? data.deletable : false,
            disable_multiple_selection: data.disable_multiple_selection,
            recordID: record && record.id,
            res_id: record && record.res_id,
            res_model: data.field.relation,
            shouldSaveLocally: true,
            title: (record ? _t("Open: ") : _t("Create ")) + (ev.target.string || data.field.string),
        }).open();
    },

});

export default ChatbotFormController;
