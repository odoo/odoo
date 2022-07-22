/** @odoo-module */

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { isAndroid, isIOS } from "@web/core/browser/feature_detection";

const { Component } = owl;

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
        this.config = configs[this.props.node.attrs.type];
    }

    openQRDialog() {
        if (
            (this.props.node.attrs.type === "apple" && isIOS()) ||
            (this.props.node.attrs.type === "google" && isAndroid())
        ) {
            this.env.services.action.doAction({
                type: "ir.actions.act_url",
                url: this.config.storeUrl,
            });
        } else {
            this.dialog.add(AppStoreQRDialog, { url: this.config.storeUrl });
        }
    }
}
AppStoreWidget.template = "hr_timesheet.AppStoreWidget";

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
AppStoreQRDialog.template = "hr_timesheet.AppStoreQRDialog";

registry.category("view_widgets").add("hr_timesheet.app_store_widget", AppStoreWidget);
