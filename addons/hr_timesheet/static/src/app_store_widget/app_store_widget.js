/** @odoo-module */

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

const { Component, xml } = owl;

const configs = {
    apple: {
        alt: "Apple App Store",
        className: "o_config_app_store",
        src: "project/static/src/img/app_store.png",
        storeUrl: "https://apps.apple.com/be/app/awesome-timesheet/id1078657549",
    },
    google: {
        alt: "Google Play Store",
        className: "o_config_play_store",
        src: "project/static/src/img/play_store.png",
        storeUrl: "https://play.google.com/store/apps/details?id=com.odoo.OdooTimesheets",
    },
};

class AppStoreWidget extends Component {
    setup() {
        this.dialog = useService("dialog");
        // WOWL TODO: check view widgets' api (props.node.attrs? Seems verbose and not particularly useful)
        this.config = configs[this.props.node.attrs.type];
    }

    openQRDialog() {
        // WOWL FIXME: if isMobile doAction url
        this.dialog.add(AppStoreQRDialog, { url: this.config.storeUrl });
    }
}
// WOWL TODO: move templates in own file
AppStoreWidget.template = xml`
<img t-att-alt="config.alt" class="img img-fluid mt-1" t-att-class="config.className" style="height: 85% !important; cursor: pointer;" t-att-src="config.src" t-on-click="openQRDialog"/>
`;

class AppStoreQRDialog extends Component {
    setup() {
        this.title = _t("Download our app");
        this.qrCodeUrl = `/report/barcode/?barcode_type=QR&value=${this.props.url}&width=256&height=256&humanreadable=1`;
    }

    viewApp() {
        window.open(this.props.url, "_blank");
    }
}
AppStoreQRDialog.components = { Dialog };
AppStoreQRDialog.template = xml`<Dialog title="title">
    <div style="text-align:center;">
        <h3>Scan this QR code to get the Awesome Timesheet app:</h3><br/><br/>
        <img class="border border-dark rounded" t-att-src="qrCodeUrl"/>
    </div>
    <t t-set-slot="footer">
        <button class="btn btn-primary" t-on-click="viewApp">View App</button>
        <button class="btn" t-on-click="props.close">Discard</button>
    </t>
</Dialog>`;

registry.category("view_widgets").add("hr_timesheet.app_store_widget", AppStoreWidget);
