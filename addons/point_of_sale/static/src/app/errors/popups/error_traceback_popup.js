/** @odoo-module */

import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { serializeDateTime } from "@web/core/l10n/dates";
const { DateTime } = luxon;

// formerly ErrorTracebackPopupWidget
export class ErrorTracebackPopup extends ErrorPopup {
    static template = "point_of_sale.ErrorTracebackPopup";
    static defaultProps = {
        confirmText: _t("Ok"),
        cancelText: _t("Cancel"),
        confirmKey: false,
        title: _t("Error with Traceback"),
        body: "",
        exitButtonIsShown: false,
        exitButtonText: _t("Exit Pos"),
    };

    setup() {
        this.pos = usePos();
    }

    get tracebackUrl() {
        const blob = new Blob([this.props.body]);
        const URL = window.URL || window.webkitURL;
        return URL.createObjectURL(blob);
    }
    get tracebackFilename() {
        return `${_t("error")} ${serializeDateTime(DateTime.now()).replace(/:|\s/gi, "-")}.txt`;
    }
    emailTraceback() {
        const address = this.pos.company.email;
        const subject = _t("IMPORTANT: Bug Report From Odoo Point Of Sale");
        window.open(
            "mailto:" +
                address +
                "?subject=" +
                (subject ? window.encodeURIComponent(subject) : "") +
                "&body=" +
                (this.props.body ? window.encodeURIComponent(this.props.body) : "")
        );
    }
}
