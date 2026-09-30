import { Component, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { generateQRCodeDataUrl } from "@point_of_sale/utils";
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
        this.dialogService = useService("dialog");
    }

    getQrCode() {
        return generateQRCodeDataUrl(this.props.customerDisplayURL);
    }

    openOnThisDevice() {
        window.open(
            this.props.customerDisplayURL,
            "newWindow",
            "width=800,height=600,left=200,top=200"
        );
        this.notification.add(_t("PoS Customer Display opened in a new window"));
    }

    showQr() {
        const qr = this.getQrCode();
        this.dialogService.add(QrDialog, {
            qrData: qr,
            parentClose: this.props.close,
        });
    }
}

class QrDialog extends Component {
    static props = ["close", "qrData", "parentClose"];
    static components = { Dialog };
    static template = xml`
        <Dialog header="false" footer="false" size="'sm'">
            <div class="d-flex flex-column align-items-center">
                <img id="CustomerDisplayqrCode" t-att-src="props.qrData" alt="Customer QR Code" class="img-fluid mb-3 square w-100"/>
                <button t-on-click="close" class="button btn btn-secondary h1 mb-3 rounded-3">
                    Close
                </button>
            </div>
        </Dialog>
    `;

    close() {
        this.props.close();
        this.props.parentClose();
    }
}
