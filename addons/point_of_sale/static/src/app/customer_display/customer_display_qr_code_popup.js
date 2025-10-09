import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { qrCodeSrc } from "@point_of_sale/utils";
import { CopyButton } from "@web/core/copy_button/copy_button";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class QrCodeCustomerDisplay extends Component {
    static template = "point_of_sale.QrCodeCustomerDisplay";
    static components = { Dialog, CopyButton };
    static props = ["close", "customerDisplayURL"];

    setup() {
        this.ui = useService("ui");
        this.notification = useService("notification");
    }

    getQrCode() {
        return qrCodeSrc(this.props.customerDisplayURL);
    }

    openOnThisDevice() {
        window.open(
            this.props.customerDisplayURL,
            "newWindow",
            "width=800,height=600,left=200,top=200"
        );
        this.notification.add(_t("PoS Customer Display opened in a new window"));
    }
}
