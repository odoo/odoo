import mobile from "@web_mobile/js/services/core";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { isAndroidApp } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";

patch(Navbar.prototype, {
    get customerFacingDisplayButtonIsShown() {
        const customerFacingDisplayButtonIsShown = super.customerFacingDisplayButtonIsShown;
        return this.supportDualDisplay || customerFacingDisplayButtonIsShown;
    },
    get supportDualDisplay() {
        return (
            isAndroidApp() &&
            mobile.methods.hasDualDisplay &&
            this.pos.config.customer_display_type === "local"
        );
    },
    openCustomerDisplay() {
        if (this.supportDualDisplay) {
            mobile.methods.hasDualDisplay().then((result) => {
                if (result.success && result.data) {
                    mobile.methods.openDualDisplay({
                        url: `${this.pos.session._base_url}/pos_customer_display/${this.pos.config.id}/${this.pos.config.access_token}`,
                    });
                } else {
                    this.notification.add(_t("Dual display is not supported on this device"));
                }
            });
        } else {
            super.openCustomerDisplay();
        }
    },
});
