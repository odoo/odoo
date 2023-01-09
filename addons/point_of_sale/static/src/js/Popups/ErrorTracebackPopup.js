/** @odoo-module */

import ErrorPopup from "@point_of_sale/js/Popups/ErrorPopup";
import Registries from "@point_of_sale/js/Registries";
import { _lt } from "@web/core/l10n/translation";

// formerly ErrorTracebackPopupWidget
class ErrorTracebackPopup extends ErrorPopup {
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
ErrorTracebackPopup.template = "ErrorTracebackPopup";
ErrorTracebackPopup.defaultProps = {
    confirmText: _lt("Ok"),
    cancelText: _lt("Cancel"),
    confirmKey: false,
    title: _lt("Error with Traceback"),
    body: "",
    exitButtonIsShown: false,
    exitButtonText: _lt("Exit Pos"),
    exitButtonTrigger: "close-pos",
};

Registries.Component.add(ErrorTracebackPopup);

export default ErrorTracebackPopup;
