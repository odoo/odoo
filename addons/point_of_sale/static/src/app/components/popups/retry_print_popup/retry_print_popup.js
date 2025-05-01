import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class RetryPrintPopup extends Component {
    static template = "point_of_sale.RetryPrintPopup";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        message: { type: String, optional: true },
        canRetry: { type: Boolean, optional: true },
        download: { type: Function, optional: true },
        retry: Function,
        close: Function,
    };
    static defaultProps = {
        title: _t("Printing failed"),
        message: _t("An unknown error occurred. Do you want to download the receipt instead?"),
    };

    onClickDownload() {
        this.props.download();
        this.props.close();
    }

    onClickRetry() {
        this.props.retry();
        this.props.close();
    }
}
