import { Activity } from "@mail/core/web/activity";

import { patch } from "@web/core/utils/patch";

patch(Activity.prototype, {
    /**
     * @param {MouseEvent} ev
     * @param {string} phoneNumber
     */
    onClickPhoneNumber(ev, phoneNumber) {
        ev.preventDefault();
        this.env.services["voip.user_agent"].makeCall({
            activity: this.env.services["mail.store"].Activity.get(this.props.activity.id),
            phone_number: phoneNumber,
            res_id: this.props.activity.res_id,
            res_model: this.props.activity.res_model,
        });
    },
});
