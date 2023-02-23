/** @odoo-module */

import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { _lt } from "@web/core/l10n/translation";

// formerly ErrorTracebackPopupWidget
export class ErrorTracebackPopup extends ErrorPopup {
    static template = "ErrorTracebackPopup";
    static defaultProps = {
        confirmText: _lt("Ok"),
        cancelText: _lt("Cancel"),
        confirmKey: false,
        title: _lt("Error with Traceback"),
        body: "",
        exitButtonIsShown: false,
        exitButtonText: _lt("Exit Pos"),
        exitButtonTrigger: "close-pos",
    };

    get tracebackUrl() {
        const blob = new Blob([this.props.body]);
        const URL = window.URL || window.webkitURL;
        return URL.createObjectURL(blob);
    }
    get tracebackFilename() {
        return `${this.env._t("error")} ${moment().format("YYYY-MM-DD-HH-mm-ss")}.txt`;
    }
    emailTraceback() {
        const address = this.env.pos.company.email;
        const subject = this.env._t("IMPORTANT: Bug Report From Odoo Point Of Sale");
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
