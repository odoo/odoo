odoo.define('web_editor.FormController', function (require) {
"use strict";
const FormController = require('web.FormController');

FormController.include({

    /**
     * @override
     */
    saveRecord: function () {
        return this._super(...arguments).then((changedFields) => {
            // update res_id with the actual record id for the Attachment, when record going to save
            // this will required for showing attachment under the media dialog
            // because of the attachment already created with res_id = 0
            const res_id = this.model.get(this.handle, {raw: true}).res_id;
            const wysiwygAttachmentsID = this.renderer.wysiwygAttachmentsID || [];
            if (wysiwygAttachmentsID.length && res_id){
                return this._rpc({
                    model: 'ir.attachment',
                    method: 'write',
                    args: [Array.from(wysiwygAttachmentsID, (attachment) => attachment.id), {
                        res_id: res_id,
                    }],
                }).then((result) => {
                    return changedFields;
                });
            }
            return changedFields;
        });
    },
});
});
