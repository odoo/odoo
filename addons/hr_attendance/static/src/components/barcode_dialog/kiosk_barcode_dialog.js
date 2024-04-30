import { useState, onWillStart } from "@odoo/owl";
import { BarcodeDialog } from "@web/webclient/barcode/barcode_scanner";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

export class AttendanceBarcodeDialog extends BarcodeDialog {
    static template = "hr_attendance.BarcodeDialog";
    static props = {
        ...BarcodeDialog,
        token: { type: String },
    };

    /**
     * @override
     */
    setup() {
        super.setup();
        this.state = useState({
            barcode: false,
        });
        this.notification = useService("notification");
        onWillStart( async () => {
            this.isFreshDb = await rpc("/hr_attendance/is_fresh_db", { token: this.props.token });
        });
    }

    /**
     * @override
     */
    get title() {
        return _t("Scan your badge's barcode");
    }

    async setBadgeID() {
        let barcode = this.state.barcode;
        if (barcode) {
            const result = await rpc("/hr_attendance/set_user_barcode", { token: this.props.token, barcode, });
            if (result) {
                this.notification.add(_t("Your badge Id is now set, you can scan your badge."), { type: 'success', });
            } else {
                this.notification.add(_t("Your badge has already been set."), { type: 'danger', });
            }
        }
    }
}
