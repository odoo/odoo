import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { PhoneField } from "@web/views/fields/phone/phone_field";

patch(PhoneField.prototype, {
    setup() {
        super.setup();
        if ("voip" in this.env.services) {
            // FIXME: this is only because otherwise @web tests would fail.
            // This is one of the major pitfalls of patching.
            this.voip = useService("voip");
            this.callService = useService("voip.call");
            this.userAgent = useService("voip.user_agent");
        }
    },
    /**
     * Called when the phone number is clicked.
     *
     * @private
     * @param {MouseEvent} ev
     */
    onLinkClicked(ev) {
        if (!this.voip?.canCall) {
            return;
        }
        if (ev.target.matches("a")) {
            ev.stopImmediatePropagation();
        }
        ev.preventDefault();
        const fieldName = ev.target.closest(".o_field_phone").getAttribute("name");
        const { record } = this.props;
        this.userAgent.makeCall({
            phone_number: record.data[fieldName],
            res_id: record.resId,
            res_model: record.resModel,
        });
    },
});
