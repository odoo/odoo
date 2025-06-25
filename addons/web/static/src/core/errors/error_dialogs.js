import { browser } from "../browser/browser";
import { Dialog } from "../dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "../registry";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { capitalize } from "../utils/strings";

import { Component, useRef, useState, markup } from "@odoo/owl";

const { DateTime } = luxon;

// This props are added by the error handler
export const standardErrorDialogProps = {
    traceback: { type: [String, { value: null }], optional: true },
    message: { type: String, optional: true },
    name: { type: String, optional: true },
    exceptionName: { type: [String, { value: null }], optional: true },
    data: { type: [Object, { value: null }], optional: true },
    subType: { type: [String, { value: null }], optional: true },
    code: { type: [Number, String, { value: null }], optional: true },
    type: { type: [String, { value: null }], optional: true },
    serverHost: { type: [String, { value: null }], optional: true },
    id: { type: [Number, { value: null }], optional: true },
    model: { type: [String, { value: null }], optional: true },
    close: Function, // prop added by the Dialog service
};

export const odooExceptionTitleMap = new Map(
    Object.entries({
        "odoo.addons.base.models.ir_mail_server.MailDeliveryException": _t("MailDeliveryException"),
        "odoo.exceptions.AccessDenied": _t("Access Denied"),
        "odoo.exceptions.MissingError": _t("Missing Record"),
        "odoo.addons.web.controllers.action.MissingActionError": _t("Missing Action"),
        "odoo.exceptions.UserError": _t("Invalid Operation"),
        "odoo.exceptions.ValidationError": _t("Validation Error"),
        "odoo.exceptions.AccessError": _t("Access Error"),
        "odoo.exceptions.Warning": _t("Warning"),
    })
);

// -----------------------------------------------------------------------------
// Generic Error Dialog
// -----------------------------------------------------------------------------
export class ErrorDialog extends Component {
    static template = "web.ErrorDialog";
    static components = { Dialog };
    static title = _t("Odoo Error");
    static showTracebackButtonText = _t("See technical details");
    static hideTracebackButtonText = _t("Hide technical details");
    static props = { ...standardErrorDialogProps };

    setup() {
        this.state = useState({
            showTraceback: false,
        });
        this.copyButtonRef = useRef("copyButton");
        this.popover = usePopover(Tooltip);
        this.contextDetails = "Occured ";
        if (this.props.serverHost) {
            this.contextDetails += `on ${this.props.serverHost} `;
        }
        if (this.props.model && this.props.id) {
            this.contextDetails += `on model ${this.props.model} and id ${this.props.id} `;
        }
        this.contextDetails += `on ${DateTime.now()
            .setZone("UTC")
            .toFormat("yyyy-MM-dd HH:mm:ss")} GMT`;
    }

    showTooltip() {
        this.popover.open(this.copyButtonRef.el, { tooltip: _t("Copied") });
        browser.setTimeout(this.popover.close, 800);
    }

    onClickClipboard() {
        browser.navigator.clipboard.writeText(
            `${this.props.name}\n\n${this.props.message}\n\n${this.contextDetails}\n\n${this.props.traceback}`
        );
        this.showTooltip();
    }
}

// -----------------------------------------------------------------------------
// Client Error Dialog
// -----------------------------------------------------------------------------
export class ClientErrorDialog extends ErrorDialog {}
ClientErrorDialog.title = _t("Odoo Client Error");

// -----------------------------------------------------------------------------
// Network Error Dialog
// -----------------------------------------------------------------------------
export class NetworkErrorDialog extends ErrorDialog {}
NetworkErrorDialog.title = _t("Odoo Network Error");

// -----------------------------------------------------------------------------
// RPC Error Dialog
// -----------------------------------------------------------------------------
export class RPCErrorDialog extends ErrorDialog {
    setup() {
        super.setup();
        this.inferTitle();
        this.traceback = this.props.traceback;
        if (this.props.data && this.props.data.debug) {
            this.traceback = `${this.props.data.debug}\nThe above server error caused the following client error:\n${this.traceback}`;
        }
    }
    inferTitle() {
        // If the server provides an exception name that we have in a registry.
        if (this.props.exceptionName && odooExceptionTitleMap.has(this.props.exceptionName)) {
            this.title = odooExceptionTitleMap.get(this.props.exceptionName).toString();
            return;
        }
        // Fall back to a name based on the error type.
        if (!this.props.type) {
            return;
        }
        switch (this.props.type) {
            case "server":
                this.title = _t("Odoo Server Error");
                break;
            case "script":
                this.title = _t("Odoo Client Error");
                break;
            case "network":
                this.title = _t("Odoo Network Error");
                break;
        }
    }

    onClickClipboard() {
        browser.navigator.clipboard.writeText(
            `${this.props.name}\n\n${this.props.message}\n\n${this.contextDetails}\n\n${this.traceback}`
        );
        this.showTooltip();
    }
}

// -----------------------------------------------------------------------------
// Warning Dialog
// -----------------------------------------------------------------------------
export class WarningDialog extends Component {
    static template = "web.WarningDialog";
    static components = { Dialog };
    static props = {
        ...standardErrorDialogProps,
        title: { type: String, optional: true },
    };

    setup() {
        this.title = this.inferTitle();
        const { data, message } = this.props;
        if (data && data.arguments && data.arguments.length > 0) {
            this.message = data.arguments[0];
        } else {
            this.message = message;
        }
    }
    inferTitle() {
        if (this.props.exceptionName && odooExceptionTitleMap.has(this.props.exceptionName)) {
            return odooExceptionTitleMap.get(this.props.exceptionName).toString();
        }
        return this.props.title || _t("Odoo Warning");
    }
}

// -----------------------------------------------------------------------------
// Redirect Warning Dialog
// -----------------------------------------------------------------------------
export class RedirectWarningDialog extends Component {
    static template = "web.RedirectWarningDialog";
    static components = { Dialog };
    static props = { ...standardErrorDialogProps };

    setup() {
        this.actionService = useService("action");
        const { data, subType } = this.props;
        const [message, actionId, buttonText, additionalContext] = data.arguments;
        this.title = capitalize(subType) || _t("Odoo Warning");
        this.message = message;
        this.actionId = actionId;
        this.buttonText = buttonText;
        this.additionalContext = additionalContext;
    }
    async onClick() {
        const options = {};
        if (this.additionalContext) {
            options.additionalContext = this.additionalContext;
        }
        if (this.actionId.help) {
            this.actionId.help = markup(this.actionId.help);
        }
        await this.actionService.doAction(this.actionId, options);
        this.props.close();
    }
}

// -----------------------------------------------------------------------------
// Error 504 Dialog
// -----------------------------------------------------------------------------
export class Error504Dialog extends Component {
    static template = "web.Error504Dialog";
    static components = { Dialog };
    static props = { ...standardErrorDialogProps };
}

// -----------------------------------------------------------------------------
// Expired Session Error Dialog
// -----------------------------------------------------------------------------
export class SessionExpiredDialog extends Component {
    static template = "web.SessionExpiredDialog";
    static components = { Dialog };
    static props = { ...standardErrorDialogProps };

    onClick() {
        browser.location.reload();
    }
}

registry
    .category("error_dialogs")
    .add("odoo.exceptions.AccessDenied", WarningDialog)
    .add("odoo.exceptions.AccessError", WarningDialog)
    .add("odoo.exceptions.MissingError", WarningDialog)
    .add("odoo.addons.web.controllers.action.MissingActionError", WarningDialog)
    .add("odoo.exceptions.UserError", WarningDialog)
    .add("odoo.exceptions.ValidationError", WarningDialog)
    .add("odoo.exceptions.RedirectWarning", RedirectWarningDialog)
    .add("odoo.http.SessionExpiredException", SessionExpiredDialog)
    .add("werkzeug.exceptions.Forbidden", SessionExpiredDialog)
    .add("504", Error504Dialog);
