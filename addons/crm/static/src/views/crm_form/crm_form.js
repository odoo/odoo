import { checkRainbowmanMessage } from "@crm/views/check_rainbowman_message";
import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";

class CrmFormRecord extends formView.Model.Record {
     /**
     * override of record _save mechanism intended to affect the main form record
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
    async _save() {
        if (this.resModel !== "crm.lead") {
            return super._save(...arguments);
        }
        let changeStage = false;
        const needsSynchronizationEmail =
            this._changes.partner_email_update === undefined
                ? this._values.partner_email_update // original value
                : this._changes.partner_email_update; // new value

        const needsSynchronizationPhone =
            this._changes.partner_phone_update === undefined
                ? this._values.partner_phone_update // original value
                : this._changes.partner_phone_update; // new value

        if (needsSynchronizationEmail && this._changes.email_from === undefined && this._values.email_from) {
            this._changes.email_from = this._values.email_from;
        }
        if (needsSynchronizationPhone && this._changes.phone === undefined && this._values.phone) {
            this._changes.phone = this._values.phone;
        }

        if ("stage_id" in this._changes) {
            changeStage = this._values.stage_id !== this.data.stage_id;
        }

        const res = await super._save(...arguments);
        if (changeStage) {
            await checkRainbowmanMessage(this.model.orm, this.model.effect, this.resId);
        }
        return res;
    }
}

class CrmFormModel extends formView.Model {
    static Record = CrmFormRecord;
    static services = [...formView.Model.services, "effect"];

    setup(params, services) {
        super.setup(...arguments);
        this.effect = services.effect;
    }
}

registry.category("views").add("crm_form", {
    ...formView,
    Model: CrmFormModel,
});
