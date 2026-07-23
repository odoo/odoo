import { browser } from "../browser/browser";
import { Dialog } from "../dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "../registry";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { capitalize } from "../utils/strings";
import { Component, markup, proxy, signal, t, useProps } from "@odoo/owl";

const { DateTime } = luxon;

// This props are added by the error handler
export const standardErrorDialogProps = {
    traceback: t.or([t.string(), t.literal(null)]).optional(),
    message: t.string().optional(),
    name: t.string().optional(),
    exceptionName: t.or([t.string(), t.literal(null)]).optional(),
    data: t.or([t.object(), t.literal(null)]).optional(),
    subType: t.or([t.string(), t.literal(null)]).optional(),
    code: t.or([t.number(), t.string(), t.literal(null)]).optional(),
    type: t.or([t.string(), t.literal(null)]).optional(),
    serverHost: t.or([t.string(), t.literal(null)]).optional(),
    id: t.or([t.number(), t.literal(null)]).optional(),
    model: t.or([t.string(), t.literal(null)]).optional(),
    close: t.function(), // prop added by the Dialog service
};

export const odooExceptionTitleMap = new Map(
    Object.entries({
        "odoo.addons.base.models.ir_mail_server.MailDeliveryException": _t("MailDeliveryException"),
        "odoo.exceptions.AccessDenied": _t("Access Denied"),
        "odoo.exceptions.MissingError": _t("Missing Record"),
        "odoo.addons.web.controllers.action.MissingActionError": _t("Missing Action"),
        "odoo.addons.base.models.ir_actions.ServerActionWithWarningsError": _t("Invalid Operation"),
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
    props = useProps({
        ...standardErrorDialogProps,
    });

    copyButtonRef = signal.ref();

    setup() {
        this.state = proxy({
            showTraceback: false,
        });
        this.popover = usePopover(Tooltip);
        let date = DateTime.now().setZone("UTC");
        if (this.props.data?.timestamp) {
            date = DateTime.fromSeconds(this.props.data.timestamp, { zone: "utc" });
        }
        this.logDate = date.toFormat("dd/MMM/yyyy HH:mm:ss", { locale: "en" });

        this.contextDetails = "Occurred ";
        if (this.props.serverHost) {
            this.contextDetails += `on ${this.props.serverHost} `;
        }
        if (this.props.model) {
            this.contextDetails += `on model ${this.props.model} `;
        }
        this.contextDetails += `on ${this.logDate}`;
    }

    showTooltip() {
        this.popover.open(this.copyButtonRef(), { tooltip: _t("Copied") });
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
// Request Entity Too Large Dialog
// -----------------------------------------------------------------------------
export class RequestEntityTooLargeErrorDialog extends ErrorDialog {}
RequestEntityTooLargeErrorDialog.title = _t("The request sent to the server was too large");

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
export const warningDialogProps = {
    ...standardErrorDialogProps,
    title: t.string().optional(),
};

export class WarningDialog extends Component {
    static template = "web.WarningDialog";
    static components = { Dialog };
    props = useProps(warningDialogProps);

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
    props = useProps({
        ...standardErrorDialogProps,
    });

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
        const options = { forceLeave: true };
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
// Unlink Blocked Error Dialog
// -----------------------------------------------------------------------------

/**
 * Shown for any `UnlinkBlockedError` (see `Base.web_unlink` server-side, in
 * `@web/../models/models.py`), whichever flow the delete came from: everything
 * this dialog needs travels in the error's `context`.
 */
export class UnlinkBlockedErrorDialog extends Component {
    static template = "web.UnlinkBlockedErrorDialog";
    static components = { Dialog };
    props = useProps({
        ...standardErrorDialogProps,
    });

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        const {
            archivable,
            model_name: modelName,
            res_model: resModel,
            res_ids: resIds,
            blocked_ids: blockedIds,
        } = this.props.data.context;
        this.archivable = archivable;
        this.resModel = resModel;
        this.resIds = resIds;
        this.blockedIds = blockedIds;
        this.isMulti = resIds.length > 1;
        this.message = this.isMulti
            ? _t("Not possible to delete all the records because some are used in %(model_name)s", {
                  model_name: modelName,
              })
            : _t("Not possible to delete the record because it is used in %(model_name)s", {
                  model_name: modelName,
              });
    }

    get archiveHint() {
        return this.isMulti
            ? _t("How about archiving them instead?")
            : _t("How about archiving it instead?");
    }

    async onArchiveClick() {
        await this.orm.call(this.resModel, "action_archive", [this.resIds]);
        // the current view has no idea any of this happened: make it reload
        const controller = this.actionService.currentController;
        if (controller) {
            await this.actionService.restore(controller.jsId);
        }
        this.props.close();
    }

    async onViewBlockedRecordsClick(ev) {
        ev.preventDefault();
        // a new action, so the user gets back through the breadcrumbs
        await this.actionService.doAction({
            name: _t("Non-deletable records"),
            type: "ir.actions.act_window",
            res_model: this.resModel,
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [["id", "in", this.blockedIds]],
            target: "current",
        });
        this.props.close();
    }
}

// -----------------------------------------------------------------------------
// Error 504 Dialog
// -----------------------------------------------------------------------------
export class Error504Dialog extends Component {
    static template = "web.Error504Dialog";
    static components = { Dialog };
    props = useProps({
        ...standardErrorDialogProps,
    });
}

// -----------------------------------------------------------------------------
// Expired Session Error Dialog
// -----------------------------------------------------------------------------
export class SessionExpiredDialog extends Component {
    static template = "web.SessionExpiredDialog";
    static components = { Dialog };
    props = useProps({
        ...standardErrorDialogProps,
    });

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
    .add("odoo.addons.base.models.ir_actions.ServerActionWithWarningsError", WarningDialog)
    .add("odoo.exceptions.UserError", WarningDialog)
    .add("odoo.exceptions.ValidationError", WarningDialog)
    .add("odoo.exceptions.RedirectWarning", RedirectWarningDialog)
    .add("odoo.addons.web.models.models.UnlinkBlockedError", UnlinkBlockedErrorDialog)
    .add("odoo.http.session.SessionExpiredException", SessionExpiredDialog)
    .add("werkzeug.exceptions.Forbidden", SessionExpiredDialog)
    .add("504", Error504Dialog);
