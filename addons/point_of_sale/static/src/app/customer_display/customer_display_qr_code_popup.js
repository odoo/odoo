import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { generateQRCodeDataUrl } from "@point_of_sale/utils";
import { CopyButton } from "@web/core/copy_button/copy_button";

export class QrCodeCustomerDisplay extends Component {
    static template = "point_of_sale.QrCodeCustomerDisplay";
    static components = { Dialog, CopyButton };
    static props = ["close", "customerDisplayURL"];

    getQrCode() {
        return generateQRCodeDataUrl(this.props.customerDisplayURL);
    }
}
