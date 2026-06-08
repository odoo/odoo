import { Component, props, types } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class RetryPrintPopup extends Component {
    static template = "point_of_sale.RetryPrintPopup";
    static components = { Dialog };
    props = props(
        {
            "title?": types.string(),
            "message?": types.string(),
            "canRetry?": types.boolean(),
            "download?": types.function(),
            "tryOnOtherPrinter?": types.boolean(),
            "onTryOtherPrinter?": types.function(),
            retry: types.function(),
            close: types.function(),
        },
        {
            title: _t("Printing failed"),
            message: _t("An unknown error occurred. Do you want to download the receipt instead?"),
        }
    );

    onClickDownload() {
        this.props.download();
        this.props.close();
    }

    onClickRetry() {
        this.props.retry();
        this.props.close();
    }

    onClickTryOnOtherPrinter() {
        this.props.onTryOtherPrinter?.();
        this.props.close();
    }
}
