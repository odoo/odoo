import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { qrCodeSrc } from "@point_of_sale/utils";
import { CopyButton } from "@web/core/copy_button/copy_button";
import { _t } from "@web/core/l10n/translation";

export class QrCodeCustomerDisplay extends Component {
    static template = "point_of_sale.QrCodeCustomerDisplay";
    static components = { Dialog, CopyButton };
    static props = ["close", "qrCodeURL", "session"];

    get qrCode() {
        const baseUrl = this.props.session._base_url;
        return qrCodeSrc(`${baseUrl}${this.props.qrCodeURL}`);
    }

    get getCustomerDisplayURL() {
        return `${this.props.session._base_url}${this.props.qrCodeURL}`;
    }

    get successText() {
        return _t("Link copied to clipboard.");
    }
}
