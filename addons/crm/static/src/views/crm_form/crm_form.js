/** @odoo-module **/

import { checkRainbowmanMessage } from "@crm/views/check_rainbowman_message";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";

/**
 * This Form Controller makes sure we display a rainbowman message
 * when the stage is won, even when we click on the statusbar.
 * When the stage of a lead is changed and data are saved, we check
 * if the lead is won and if a message should be displayed to the user
 * with a rainbowman like when the user click on the button "Mark Won".
 */

class CrmFormController extends formView.Controller {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.effect = useService("effect");
        this.changedStage = false;
    }

    /**
     * Main method used when saving the record hitting the "Save" button.
     * We check if the stage_id field was altered and if we need to display a rainbowman
     * message.
     *
     * This method will also simulate a real "force_save" on the email and phone
     * when needed. The "force_save" attribute only works on readonly field. For our
     * use case, we need to write the email and the phone even if the user didn't
     * change them, to synchronize those values with the partner (so the email / phone
     * inverse method can be called).
     *
     * We base this synchronization on the value of "partner_phone_update"
     * and "partner_email_update", which are computed fields that hold a value
     * whenever we need to synch.
     *
     * @override
     */
    async onWillSaveRecord(record) {
        const recordID = record.__bm_handle__;
        const localData = record.model.__bm__.localData[recordID];
        const changes = localData._changes || {};

        const needsSynchronizationEmail =
            changes.partner_email_update === undefined
                ? localData.data.partner_email_update // original value
                : changes.partner_email_update; // new value

        const needsSynchronizationPhone =
            changes.partner_phone_update === undefined
                ? localData.data.partner_phone_update // original value
                : changes.partner_phone_update; // new value

        if (
            needsSynchronizationEmail &&
            changes.email_from === undefined &&
            localData.data.email_from
        ) {
            changes.email_from = localData.data.email_from;
        }
        if (needsSynchronizationPhone && changes.phone === undefined && localData.data.phone) {
            changes.phone = localData.data.phone;
        }
        if (!localData._changes && Object.keys(changes).length) {
            localData._changes = changes;
        }

        if ("stage_id" in changes && changes.stage_id) {
            const bm = record.model.__bm__;
            let oldStageId = false;
            if (bm.localData[recordID].data.stage_id) {
                oldStageId = bm.get(bm.localData[recordID].data.stage_id).data.id;
            }
            const newStageId = bm.get(bm.localData[recordID]._changes.stage_id).data.id;
            this.changedStage = oldStageId !== newStageId;
        }
    }

    async onRecordSaved(record) {
        if (this.changedStage) {
            checkRainbowmanMessage(this.orm, this.effect, record.resId);
        }
    }
}

registry.category("views").add("crm_form", {
    ...formView,
    Controller: CrmFormController,
});
