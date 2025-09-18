import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/ui/dialog/dialog";
export class CustomerFacingQR extends Component {
    static template = "point_of_sale.CustomerFacingQR";
    static components = { Dialog };
    static props = {
        qrCode: String,
        name: String,
        amount: String,
        close: Function,
    };

    setup() {
        this.title = _t("Please scan the QR code with %s", this.props.name);
    }
}
