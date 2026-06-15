import { Component, xml, useProps, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { generateQRCodeDataUrl } from "@point_of_sale/utils";
import { CopyButton } from "@web/core/copy_button/copy_button";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class QrCodeCustomerDisplay extends Component {
    static template = "point_of_sale.QrCodeCustomerDisplay";
    static components = { Dialog, CopyButton };
    props = useProps({
        close: t.function(),
        customerDisplayURL: t.string(),
    });

    setup() {
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
    }

    getQrCode() {
        return generateQRCodeDataUrl(this.props.customerDisplayURL, { useThemeQr: true });
    }

    async getScreenFeatures() {
        let windowFeatures = "width=800,height=600,left=200,top=200";
        let usedFallback = false;

        if ("getScreenDetails" in window) {
            // https://developer.mozilla.org/en-US/docs/Web/API/Window/getScreenDetails
            try {
                const screenDetails = await window.getScreenDetails();
                if (screenDetails.screens.length >= 2) {
                    const secondScreen = screenDetails.screens.find(
                        (screen) => screen !== screenDetails.currentScreen
                    );

                    if (secondScreen) {
                        windowFeatures = [
                            `left=${secondScreen.availLeft}`,
                            `top=${secondScreen.availTop}`,
                            `width=${secondScreen.availWidth}`,
                            `height=${secondScreen.availHeight}`,
                        ].join(",");
                    }
                }
            } catch {
                usedFallback = true;
            }
        }
        return { windowFeatures, usedFallback };
    }

    async openOnThisDevice() {
        const { windowFeatures, usedFallback } = await this.getScreenFeatures();
        window.open(this.props.customerDisplayURL, "customerDisplay", windowFeatures);

        if (usedFallback) {
            this.notification.add(
                _t("Customer Display opened in a new window. Allow popups to use a second screen.")
            );
        } else {
            this.notification.add(_t("Customer Display opened in a new window"));
        }
        this.props.close();
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
    props = useProps({
        close: t.function(),
        qrData: t.string(),
        parentClose: t.function(),
    });
    static components = { Dialog };
    static template = xml`
        <Dialog header="false" size="'sm'" bodyClass="'d-flex justify-content-center'" contentClass="'pt-4 pb-3'">
            <img id="CustomerDisplayqrCode" t-att-src="this.props.qrData" alt="Customer QR Code" class="img-fluid w-50"/>
            <t t-set-slot="footer">
                <button class="btn btn-secondary mx-auto" t-on-click="this.close">Discard</button>
            </t>
        </Dialog>
    `;

    close() {
        this.props.close();
        this.props.parentClose();
    }
}
