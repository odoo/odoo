/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillUnmount } from "@odoo/owl";

const { DateTime } = luxon;

export class WelcomePage extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.state = useState({ today: this.getCurrentTime(), qrCode: false });
        this.timeInterval = setInterval(() => (this.state.today = this.getCurrentTime()), 1000);
        this.props.resetData();
        // Make the qr code only when self_check_in field is true from backend.
        if (this.props.stationInfo.self_check_in) {
            this._getQrCodeData();
            this.qrCodeInterval = setInterval(() => this._getQrCodeData(), 3600000); // 1 hour
        }
        onWillUnmount(() => {
            clearInterval(this.timeInterval);
            if (this.props.stationInfo.self_check_in) {
                clearInterval(this.qrCodeInterval);
            }
        });
    }

    getCurrentTime() {
        return DateTime.now().toLocaleString(DateTime.TIME_SIMPLE);
    }

    /**
     * @private
     */
    async _getQrCodeData() {
        const response = await this.rpc(
            `/kiosk/${this.props.stationInfo.id}/get_tmp_code/${this.props.token}`
        );
        const token = encodeURIComponent(response[0] + response[1]);
        this.state.qrCode = this._makeQrCodeData(
            `${window.location.origin}/kiosk/${this.props.stationInfo.id}/mobile/${token}`
        );
    }

    /**
     * @private
     */
    _makeQrCodeData(url) {
        const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
        const qrCodeSVG = new XMLSerializer().serializeToString(codeWriter.write(url, 250, 250));
        return "data:image/svg+xml;base64," + window.btoa(qrCodeSVG);
    }
}

WelcomePage.template = "frontdesk.WelcomePage";
WelcomePage.props = {
    companyName: String,
    currentLang: String,
    langs: [Object, Boolean],
    onChangeLang: Function,
    token: String,
    resetData: Function,
    showScreen: Function,
    stationInfo: Object,
};

registry.category("frontdesk_screens").add("WelcomePage", WelcomePage);
