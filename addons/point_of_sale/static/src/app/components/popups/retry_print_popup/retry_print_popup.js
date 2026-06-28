import { Component, props, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class RetryPrintPopup extends Component {
    static template = "point_of_sale.RetryPrintPopup";
    static components = { Dialog };
    props = props({
        title: t.string().optional(_t("Printing failed")),
        message: t
            .string()
            .optional(
                _t("An unknown error occurred. Do you want to download the receipt instead?")
            ),
        canRetry: t.boolean().optional(),
        download: t.function().optional(),
        tryOnOtherPrinter: t.boolean().optional(),
        onTryOtherPrinter: t.function().optional(),
        retry: t.function(),
        close: t.function(),
    });

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
